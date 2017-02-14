# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import hashlib
import hmac
import logging
import math
import random

import OpenSSL

from django.conf import settings
from django.db import models, IntegrityError
from django.utils import six
from django.utils.encoding import force_bytes, force_text, python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.six.moves import range, zip
from django.utils.translation import ugettext_lazy as _

from demos_voting.base.models import Election, Question, Option, Ballot, Part, PQuestion, POption, Task
from demos_voting.base.utils import base32, crypto
from demos_voting.base.utils.hashers import get_hasher
from demos_voting.election_authority import managers

logger = logging.getLogger(__name__)
random = random.SystemRandom()


class Election(Election):

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    modified_at = models.DateTimeField(_("modified at"), auto_now=True)
    setup_started_at = models.DateTimeField(_("setup started at"), null=True, default=None)
    setup_ended_at = models.DateTimeField(_("setup ended at"), null=True, default=None)

    @cached_property
    def curve_nid(self):
        return OpenSSL.crypto.get_elliptic_curve(self.curve_name)._nid

    def save(self, *args, **kwargs):
        if not self.id:
            while True:
                last_id = (Election.objects.values('id').last() or {}).get('id')
                self.id = base32.encode(base32.decode(last_id) + 1) if last_id else '0'
                try:
                    return super(Election, self).save(*args, **kwargs)
                except IntegrityError:
                    continue
        else:
            return super(Election, self).save(*args, **kwargs)

    def generate_votecode_length(self):
        if self.votecode_type != Election.VOTECODE_TYPE_LONG:
            self.votecode_length = None

    def generate_security_code_length(self, optionss=None):
        if self.security_code_type == Election.SECURITY_CODE_TYPE_NONE:
            self.security_code_length = None
        else:
            if self.votecode_type == Election.VOTECODE_TYPE_LONG:
                self.security_code_length = self.SECURITY_CODE_MAX_LENGTH
            else:
                length = self._generate_security_code_length(optionss) if optionss else self._security_code_length
                self.security_code_length = max(
                    self.SECURITY_CODE_MIN_LENGTH,
                    min(self.SECURITY_CODE_MAX_LENGTH, length)
                )

    def generate_keypair(self):
        if self.votecode_type == Election.VOTECODE_TYPE_LONG:
            self.keypair = OpenSSL.crypto.PKey()
            self.keypair.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)
        elif self.votecode_type == Election.VOTECODE_TYPE_SHORT:
            self.keypair = None

    def generate_certificate(self):
        if self.votecode_type == Election.VOTECODE_TYPE_LONG:
            self.certificate = OpenSSL.crypto.X509()

            ca_key_path = getattr(settings, 'DEMOS_VOTING_CA_PKEY_FILE', '')
            ca_certificate_path = getattr(settings, 'DEMOS_VOTING_CA_CERT_FILE', '')

            if ca_key_path or ca_certificate_path:
                ca_key_passphrase = getattr(settings, 'DEMOS_VOTING_CA_PKEY_PASSPHRASE', '')

                with open(ca_key_path, 'r') as ca_pkey_file:
                    ca_keypair = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, ca_pkey_file.read(),
                                                            force_bytes(ca_key_passphrase))

                with open(ca_certificate_path, 'r') as ca_cert_file:
                    ca_certificate = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, ca_cert_file.read())

                self.certificate.set_subject(ca_certificate.get_subject())

            else: # self-signed certificate
                ca_keypair = self.keypair
                ca_certificate = self.certificate

            validity = datetime.timedelta(365)

            self.certificate.get_subject().CN = "DEMOS Voting - Election ID: %s" % self.id
            self.certificate.set_issuer(ca_certificate.get_subject())
            self.certificate.set_version(3)
            self.certificate.set_serial_number(base32.decode(self.id))
            self.certificate.set_notBefore(force_bytes(self.setup_started_at.strftime('%Y%m%d%H%M%S%z')))
            self.certificate.set_notAfter(force_bytes((self.setup_started_at + validity).strftime('%Y%m%d%H%M%S%z')))
            self.certificate.set_pubkey(self.keypair)
            self.certificate.sign(ca_keypair, str('sha256'))

        elif self.votecode_type == Election.VOTECODE_TYPE_SHORT:
            self.certificate = None


class Question(Question):

    def generate_trustee_keys(self):
        self.trustee_keys = self._crypto[0]

    def generate_commitment_key(self):
        self.commitment_key = self._crypto[1]

    @cached_property
    def _crypto(self):
        return crypto.KeyGen(self.election.trustees.count(), self.election.curve_nid)


class Option(Option):
    pass


class Ballot(Ballot):

    def generate_credential(self):
        randomness = random.getrandbits(self.election.credential_length * 5)
        self.credential = base32.encode(randomness, self.election.credential_length)
        hasher = get_hasher(self.election.DEFAULT_HASHER_IDENTIFIER)
        self.credential_hash = hasher.hash(self.credential)

    @cached_property
    def _crypto(self):
        ballot = []
        for question in self.election.questions.all():
            trustee_keys = question.trustee_keys
            commitment_key = question.commitment_key
            serial_number = force_bytes(self.serial_number)
            options = [int(not option.is_blank) for option in question.options.all()]
            permutations = [part.questions.all()[question.index].permutation for part in self.parts.all()]
            curve_nid = self.election.curve_nid
            parts = crypto.BallotGen(trustee_keys, commitment_key, serial_number, options, permutations, curve_nid)
            ballot.append(parts)
        return list(zip(*ballot))


class Part(Part):

    def generate_security_code(self):
        if self.election.security_code_type == Election.SECURITY_CODE_TYPE_NONE:
            self.security_code = None
        else:
            # Split options into groups, one for each security code's block.

            if self.election.type == Election.TYPE_ELECTION:
                # The first group is always the party list, followed by one
                # group for each party's candidates. Candidate lists have a
                # special structure by grouping the options that correspond
                # to the same party (all parties always have the same number
                # of candidates, including the blank ones).

                parties = self.election.questions.all()[0].options.all()
                candidates = self.election.questions.all()[1].options.all()

                groups = [tuple(parties)] + [
                    options for options in zip(*([iter(candidates)] * (len(candidates) // len(parties))))
                ]

            elif self.election.type == Election.TYPE_REFERENDUM:
                groups = [tuple(question.options.all()) for question in self.election.questions.all()]

            # If the security code has enough bits to cover all permutations
            # for all groups, then we generate a random permutation index for
            # each one of them. Otherwise, the randomness extractor will take
            # the security code and the group's index as source and generate
            # a "long" pseudo-random permutation index. In that case, the
            # security code will be a random value.

            s = 0
            s_max = 0

            if self.election.security_code_length >= self.election._security_code_length:
                for group in groups:
                    p_max = math.factorial(len(group)) - 1
                    p = None
                    while p is None or p > p_max:
                        p = random.getrandbits(p_max.bit_length())
                    s |= (p << s_max.bit_length())
                    s_max |= (p_max << s_max.bit_length())

            # Fill (the remainder of) the security code with random bits.

            security_code_length = self.election.security_code_length

            if self.election.security_code_type == Election.SECURITY_CODE_TYPE_NUMERIC:
                base = 10
                encode = lambda s, l: force_text(s).zfill(l)
            elif self.election.security_code_type == Election.SECURITY_CODE_TYPE_ALPHANUMERIC:
                base = 32
                encode = lambda s, l: base32.encode(s, l)

            s_enc_max = sum(base ** i for i in range(security_code_length)) * (base - 1)
            r_max = (s_enc_max - s_max) >> s_max.bit_length()

            if r_max > 0:
                r = None
                while r is None or r > r_max:
                    r = random.getrandbits(r_max.bit_length())
                s |= (r << s_max.bit_length())

            self.security_code = encode(s, security_code_length)[-security_code_length:]

    @cached_property
    def _crypto(self):
        return self.ballot._crypto[(Part.TAG_A, Part.TAG_B).index(self.tag)]


class PQuestion(PQuestion):

    def generate_zk(self):
        self.zk = self._crypto['ZK']

    @cached_property
    def _crypto(self):
        return self.part._crypto[self.index]

    @cached_property
    def _long_votecode_hash_config(self):
        config = None
        if settings.DEMOS_VOTING_LONG_VOTECODE_HASH_REUSE_SALT:
            config = get_hasher(self.election.DEFAULT_HASHER_IDENTIFIER).config()
        return config

    @cached_property
    def _short_votecodes(self):
        short_votecodes = [force_text(i) for i in range(1, self.options.count() + 1)]
        random.shuffle(short_votecodes)
        return short_votecodes


class POption(POption):

    def generate_votecode(self):
        if self.election.votecode_type == Election.VOTECODE_TYPE_LONG:
            length = self.election.votecode_length
            permutation = self.question.permutation

            serial_number = force_text(self.ballot.serial_number)
            option_index = force_text(permutation.index(self.index)).zfill(len(force_text(len(permutation) - 1)))
            question_index = force_text(self.question.index).zfill(len(force_text(self.part.questions.count() - 1)))

            key = self.ballot.credential + self.part.security_code
            msg = serial_number + self.part.tag + question_index + option_index
            digest = hmac.new(force_bytes(key), force_bytes(msg), hashlib.sha256).digest()

            self.votecode = base32.encode_from_bytes(digest, length)[-length:]

            hasher = get_hasher(self.election.DEFAULT_HASHER_IDENTIFIER)
            config = self.question._long_votecode_hash_config or hasher.config()

            self.votecode_hash = hasher.hash(self.votecode, config)

        elif self.election.votecode_type == Election.VOTECODE_TYPE_SHORT:
            self.votecode = self.question._short_votecodes[self.index]
            self.votecode_hash = None

    def generate_receipt(self):
        if self.election.votecode_type == Election.VOTECODE_TYPE_LONG:
            signature = OpenSSL.crypto.sign(self.election.keypair, self.votecode, str('sha256'))
            self.receipt = base32.encode_from_bytes(signature, (self.election.keypair.bits() + 4) // 5)
        elif self.election.votecode_type == Election.VOTECODE_TYPE_SHORT:
            randomness = random.getrandbits(self.election.receipt_length * 5)
            self.receipt = base32.encode(randomness, self.election.receipt_length)

    def generate_commitment(self):
        self.commitment = self._crypto[:-1]

    def generate_zk1(self):
        self.zk1 = self._crypto[-1]

    @cached_property
    def _crypto(self):
        return self.question._crypto['Row'][self.index]


class Task(Task):
    pass


@python_2_unicode_compatible
class Trustee(models.Model):

    election = models.ForeignKey('Election')
    email = models.EmailField(_('email address'))

    objects = managers.TrusteeManager()

    class Meta:
        default_related_name = 'trustees'
        ordering = ['election', 'email']
        unique_together = ['election', 'email']
        verbose_name = _("trustee")
        verbose_name_plural = _("trustees")

    def natural_key(self):
        return self.election.natural_key() + (self.email,)

    natural_key.dependencies = ['Election']

    def __str__(self):
        return self.email

