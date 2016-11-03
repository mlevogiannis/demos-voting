# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import logging
import math
import os
import random

import OpenSSL

from django.conf import settings
from django.db import models
from django.utils import six
from django.utils.encoding import force_bytes, force_text
from django.utils.six.moves import range
from django.utils.translation import ugettext_lazy as _

from demos_voting.common.models import (Election, Ballot, Part, Question, Option_P, Option_C, PartQuestion, Task,
    PrivateApiUser, PrivateApiNonce)
from demos_voting.common.utils import base32
from demos_voting.common.utils.hashers import get_hasher

logger = logging.getLogger(__name__)
random = random.SystemRandom()


class Election(Election):

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    modified_at = models.DateTimeField(_("modified at"), auto_now=True)
    setup_started_at = models.DateTimeField(_("setup started at"), null=True, default=None)
    setup_ended_at = models.DateTimeField(_("setup ended at"), null=True, default=None)

    def generate_key(self):

        self.key = OpenSSL.crypto.PKey()
        self.key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)

    def generate_cert(self):

        self.cert = OpenSSL.crypto.X509()

        ca_pkey_path = getattr(settings, 'DEMOS_VOTING_CA_PKEY_FILE', '')
        ca_cert_path = getattr(settings, 'DEMOS_VOTING_CA_CERT_FILE', '')

        if ca_pkey_path or ca_cert_path:

            ca_pkey_passphrase = getattr(settings, 'DEMOS_VOTING_CA_PKEY_PASSPHRASE', '')

            with open(ca_pkey_path, 'r') as ca_pkey_file:
                ca_key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, ca_pkey_file.read(),
                                                        force_bytes(ca_pkey_passphrase))

            with open(ca_cert_path, 'r') as ca_cert_file:
                ca_cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, ca_cert_file.read())

            self.cert.set_subject(ca_cert.get_subject())

        else: # self-signed certificate

            ca_key = self.key
            ca_cert = self.cert

        validity_period = datetime.timedelta(365)

        self.cert.get_subject().CN = "DEMOS Voting - Election ID: %s" % self.id
        self.cert.set_issuer(ca_cert.get_subject())
        self.cert.set_version(3)
        self.cert.set_serial_number(base32.decode(self.id))
        self.cert.set_notBefore(force_bytes(self.setup_started_at.strftime('%Y%m%d%H%M%S%z')))
        self.cert.set_notAfter(force_bytes((self.setup_started_at+validity_period).strftime('%Y%m%d%H%M%S%z')))
        self.cert.set_pubkey(self.key)
        self.cert.sign(ca_key, str('sha256'))

    def generate_security_code_length(self):

        if self.security_code_type_is_none:
            self.security_code_length = None
        else:
            self.security_code_length = max(
                self.SECURITY_CODE_MIN_LENGTH, min(
                    self.SECURITY_CODE_MAX_LENGTH, self._security_code_full_length
                )
            )


class Ballot(Ballot):
    pass


class Part(Part):

    def generate_credential(self):

        bytes = os.urandom(self.election.credential_length)
        length = (self.election.credential_length * 8 + 4) // 5
        self.credential = base32.encode_from_bytes(bytes, length)

        hasher = get_hasher(self.election.DEFAULT_HASHER_IDENTIFIER)
        self.credential_hash = hasher.hash(self.credential)

    def generate_security_code(self):

        if self.election.security_code_type_is_none:
            self.security_code = None
        else:

            # Split options into groups, one for each security code's block.

            if self.election.type_is_election:

                # The first group is always the party list, followed by one
                # group for each party's candidates. Candidate lists have a
                # special structure by grouping the options that correspond
                # to the same party (all parties always have the same number
                # of candidates, including the blank ones).

                parties = self.election.questions.all()[0].options_p.all()
                candidates = self.election.questions.all()[1].options_p.all()

                groups = [list(parties)] + [
                    list(options) for options in zip(*([iter(candidates)] * (len(candidates) // len(parties))))
                ]

            elif self.election.type_is_referendum:
                groups = [list(question.options_p.all()) for question in self.election.questions.all()]

            # If the security code has enough bits to cover all permutations
            # for all groups, then we generate a random permutation index for
            # each one of them. Otherwise, the randomness extractor will take
            # the security code and the group's index as source and generate
            # a "long" pseudo-random permutation index. In that case, the
            # security code will be a random value.

            s = 0
            s_max = 0

            if self.election.security_code_length >= self.election._security_code_full_length:

                for group in groups:
                    p_max = math.factorial(len(group)) - 1

                    p = None
                    while p is None or p > p_max:
                        p = random.getrandbits(p_max.bit_length())

                    s |= (p << s_max.bit_length())
                    s_max |= (p_max << s_max.bit_length())

            # Fill (the remainder of) the security code with random bits.

            base = 10 if self.election.security_code_type_is_numeric else 32
            s_enc_max = sum(base ** i for i in range(self.election.security_code_length)) * (base - 1)

            r_max = (s_enc_max - s_max) >> s_max.bit_length()

            if r_max > 0:
                r = None
                while r is None or r > r_max:
                    r = random.getrandbits(r_max.bit_length())
                s |= (r << s_max.bit_length())

            # Finally, encode the security code.

            security_code_length = self.election.security_code_length

            if self.election.security_code_type_is_numeric:
                security_code = force_text(s).zfill(security_code_length)
            elif self.election.security_code_type_is_alphanumeric:
                security_code = base32.encode(s, security_code_length)

            self.security_code = security_code[-security_code_length:]


class Question(Question):
    pass


class Option_P(Option_P):
    pass


class Option_C(Option_C):

    def generate_votecode(self):

        if self.election.votecode_type_is_long:
            reuse_salt = settings.DEMOS_VOTING_LONG_VOTECODE_HASH_REUSE_SALT
            hasher = get_hasher(self.election.DEFAULT_HASHER_IDENTIFIER)
            config = hasher.config() if not reuse_salt else self.partquestion._long_votecode_hash_config
            self.votecode = self._generate_long_votecode()
            self.votecode_hash = hasher.hash(self.votecode, config)
        else:
            self.votecode = self.partquestion._short_votecodes[self.index]
            self.votecode_hash = None

    def generate_receipt(self):

        if self.election.votecode_type_is_long:
            length = (self.election.key.bits() + 4) // 5
            signature = OpenSSL.crypto.sign(self.election.key, self.votecode, str('sha256'))
            self.receipt = base32.encode_from_bytes(signature, length)
        else:
            randomness = random.getrandbits(self.election.receipt_length * 5)
            self.receipt = base32.encode(randomness, self.election.receipt_length)


class PartQuestion(PartQuestion):

    def generate_common_votecode_data(self):

        if self.election.votecode_type_is_long:
            if settings.DEMOS_VOTING_LONG_VOTECODE_HASH_REUSE_SALT:
                hasher = get_hasher(self.election.DEFAULT_HASHER_IDENTIFIER)
                self._long_votecode_hash_config = hasher.config()
        else:
            self._short_votecodes = [force_text(i) for i in range(1, self.options_c.count() + 1)]
            random.shuffle(self._short_votecodes)


class Task(Task):
    pass


class PrivateApiUser(PrivateApiUser):
    pass


class PrivateApiNonce(PrivateApiNonce):
    pass

