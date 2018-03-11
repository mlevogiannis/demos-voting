from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import hashlib
import hmac
import itertools
import math
import random
import string

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, load_pem_private_key
from cryptography.x509.oid import NameOID

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.urls import reverse
from django.utils.encoding import force_bytes, force_text
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from six.moves import range

from demos_voting.base.fields import JSONField
from demos_voting.base.models import (
    BaseAdministrator, BaseBallot, BaseBallotOption, BaseBallotPart, BaseBallotQuestion, BaseElection,
    BaseElectionOption, BaseElectionQuestion, BaseTrustee,
)
from demos_voting.base.utils import base32, hasher
from demos_voting.base.utils.compat import int_from_bytes
from demos_voting.election_authority.managers import (
    BallotOptionManager, BallotPartManager, BallotQuestionManager, ElectionOptionManager, ElectionQuestionManager,
)
from demos_voting.election_authority.utils import crypto, luhn, permute

random = random.SystemRandom()


def election_private_key_path(election, filename):
    return "election_authority/elections/%s/private_key.pem" % election.slug


class Election(BaseElection):
    STATE_CHOICES = (
        (BaseElection.STATE_SETUP, _("Setup")),
        (BaseElection.STATE_COMPLETED, _("Completed")),
        (BaseElection.STATE_FAILED, _("Failed")),
        (BaseElection.STATE_CANCELLED, _("Cancelled")),
    )

    private_key_file = models.FileField(_("private key"), upload_to=election_private_key_path, null=True, blank=True)
    state = models.CharField(_("state"), max_length=32, choices=STATE_CHOICES, default=BaseElection.STATE_SETUP)
    setup_started_at = models.DateTimeField(_("setup started at"), null=True, blank=True)
    setup_ended_at = models.DateTimeField(_("setup ended at"), null=True, blank=True)
    tasks = models.ManyToManyField('base.Task', related_name='+', related_query_name='+')

    def get_absolute_url(self):
        return reverse('election-authority:election-detail', args=[self.slug])

    def generate_commitment_key(self):
        """
        Generate the election's commitment key.
        """
        self.commitment_key = self._crypto[1]

    @cached_property
    def _crypto(self):
        return crypto.key_gen(self.trustees.count())

    def generate_private_key(self):
        """
        If the vote-code type is long then generate the election's private key.
        """
        if self.vote_code_type == self.VOTE_CODE_TYPE_SHORT:
            self.private_key_file = None
        elif self.vote_code_type == self.VOTE_CODE_TYPE_LONG:
            self._private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            if self.pk:
                private_key_file = ContentFile(self._private_key.private_bytes(
                    encoding=Encoding.PEM,
                    format=PrivateFormat.PKCS8,
                    encryption_algorithm=NoEncryption(),
                ))
                self.private_key_file.save("private_key.pem", private_key_file, save=False)

    @property
    def private_key(self):
        if not hasattr(self, '_private_key'):
            if not self.private_key_file:
                return None
            else:
                self._private_key = load_pem_private_key(
                    data=self.private_key_file.read(),
                    password=None,
                    backend=default_backend(),
                )
        return self._private_key

    def generate_certificate(self):
        """
        If the vote-code type is long then generate the election's certificate.
        """
        if self.vote_code_type == self.VOTE_CODE_TYPE_SHORT:
            self.certificate_file = None
        elif self.vote_code_type == self.VOTE_CODE_TYPE_LONG:
            # Load the issuer's private key and certificate (if specified).
            issuer_settings = getattr(settings, 'DEMOS_VOTING_CERTIFICATE_ISSUER', {})
            issuer_private_key_path = issuer_settings.get('private_key_path')
            issuer_certificate_path = issuer_settings.get('certificate_path')
            assert ((issuer_private_key_path and issuer_certificate_path) or
                    (not issuer_private_key_path and not issuer_certificate_path))
            if issuer_private_key_path or issuer_certificate_path:
                # Load the issuer's private key and certificate.
                with open(issuer_private_key_path, 'rb') as issuer_private_key_file:
                    issuer_private_key_password = issuer_settings.get('private_key_password')
                    issuer_private_key = load_pem_private_key(
                        data=issuer_private_key_file.read(),
                        password=force_bytes(issuer_private_key_password) if issuer_private_key_password else None,
                        backend=default_backend(),
                    )
                with open(issuer_certificate_path, 'rb') as issuer_certificate_file:
                    issuer_certificate = x509.load_pem_x509_certificate(
                        data=issuer_certificate_file.read(),
                        backend=default_backend(),
                    )
            else:
                # The issued certificate will be self-signed.
                issuer_private_key = None
                issuer_certificate = None
            # Generate the election's certificate.
            builder = x509.CertificateBuilder()
            subject = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, self.slug),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, settings.DEMOS_VOTING_SITE_NAME),
            ])
            builder = builder.subject_name(subject)
            builder = builder.issuer_name(issuer_certificate.subject if issuer_certificate else subject)
            builder = builder.not_valid_before(self.created_at)
            builder = builder.not_valid_after(self.created_at + datetime.timedelta(365))
            builder = builder.serial_number(x509.random_serial_number())
            builder = builder.public_key(self.private_key.public_key())
            self._certificate = builder.sign(
                private_key=issuer_private_key or self.private_key,
                algorithm=hashes.SHA256(),
                backend=default_backend(),
            )
            if self.pk:
                certificate_file = ContentFile(self._certificate.public_bytes(encoding=Encoding.PEM))
                self.certificate_file.save("certificate.pem", certificate_file, save=False)

    def generate_vote_code_length(self):
        """
        If the vote-code type is long then set the vote-codes' length.
        """
        if self.vote_code_type == self.VOTE_CODE_TYPE_SHORT:
            self.vote_code_length = None
        elif self.vote_code_type == self.VOTE_CODE_TYPE_LONG:
            self.vote_code_length = self.LONG_VOTE_CODE_LENGTH

    def generate_security_code_length(self):
        """
        If the security code type is short then calculate the security code's
        length from the number of questions and the number of their options.
        """
        if self.vote_code_type == self.VOTE_CODE_TYPE_SHORT:
            self.security_code_length = min(self.security_code_ideal_length, self.SECURITY_CODE_MAX_LENGTH)
        elif self.vote_code_type == self.VOTE_CODE_TYPE_LONG:
            self.security_code_length = None

    @cached_property
    def security_code_ideal_length(self):
        option_counts = [question.option_count for question in self.questions.all()]
        if self.type == self.TYPE_PARTY_CANDIDATE:
            option_counts = [option_counts[0]] + [option_counts[1] // option_counts[0]] * option_counts[0]
        s_max = 0
        for option_count in option_counts:
            s_max |= (math.factorial(option_count) - 1) << s_max.bit_length()
        return len(force_text(s_max)) + 1  # + 1 for the check character


class ElectionQuestion(BaseElectionQuestion):
    objects = ElectionQuestionManager()


class ElectionOption(BaseElectionOption):
    objects = ElectionOptionManager()


class Ballot(BaseBallot):
    pass


class BallotPart(BaseBallotPart):
    credential = models.TextField(_("credential"))
    credential_hash = models.TextField(_("credential hash"))
    security_code = models.CharField(_("security code"), max_length=32, null=True, blank=True)

    objects = BallotPartManager()

    def generate_credential(self):
        """
        Generate a random credential.
        """
        randomness = random.getrandbits(self.election.credential_length * 5)
        self.credential = base32.encode(randomness, self.election.credential_length)

    def generate_credential_hash(self):
        """
        Generate the credential's hash.
        """
        self.credential_hash = hasher.encode(self.credential, hasher.salt())

    def generate_security_code(self):
        """
        Generate a random security code if the vote-code type is short.
        """
        if self.election.vote_code_type == self.election.VOTE_CODE_TYPE_SHORT:
            if self.election.security_code_length is None:
                self.security_code = None
            else:
                option_counts = [question.option_count for question in self.election.questions.all()]
                if self.election.type == self.election.TYPE_PARTY_CANDIDATE:
                    # For the purposes of security code generation, each candidate
                    # group will be treated as a separate "question".
                    option_counts = [option_counts[0]] + [option_counts[1] // option_counts[0]] * option_counts[0]
                # Check the security code's "capacity".
                if self.election.security_code_length == self.election.security_code_ideal_length:
                    # Generate a random permutation index for each question and
                    # append it to the security code.
                    s = 0
                    s_max = 0
                    for option_count in option_counts:
                        p_max = math.factorial(option_count) - 1
                        p = None
                        while p is None or p > p_max:
                            p = random.getrandbits(p_max.bit_length())
                        s |= (p << s_max.bit_length())
                        s_max |= (p_max << s_max.bit_length())
                    # Encode the security code.
                    chars = string.digits
                    value = force_text(s).zfill(self.election.security_code_length - 1)
                else:
                    # Generate a random string to be used as the security code. It
                    # will be used as the source to a randomness extractor in order
                    # to generate permutation indices greater than those that could
                    # be encoded in the security code.
                    chars = string.digits
                    value = ''.join(random.choice(chars) for i in range(self.election.security_code_length - 1))
                # Append the check character to the final value.
                self.security_code = '%s%s' % (value, luhn.generate_check_character(value, chars))
        elif self.election.vote_code_type == self.election.VOTE_CODE_TYPE_LONG:
            self.security_code = None

    def get_security_code_display(self):
        return self.security_code


class BallotQuestion(BaseBallotQuestion):
    zk1 = JSONField(_("zero-knowledge proof ZK1"))

    objects = BallotQuestionManager()

    @cached_property
    def permutation(self):
        """
        Generate the permutation array from the part's security code if the
        vote-code type is short or a random permutation array if the vote-code
        type is long.
        """
        option_counts = [question.option_count for question in self.election.questions.all()]
        if self.election.type == self.election.TYPE_PARTY_CANDIDATE:
            # For the purposes of security code generation, each candidate
            # group will be treated as a separate "question". The first
            # question corresponds to the party question, the other questions
            # correspond to the candidate groups of the candidate question.
            option_counts = [option_counts[0]] + [option_counts[1] // option_counts[0]] * option_counts[0]
        # The candidate question of a party-candidate type of election requires
        # special handling.
        question_index = self.election_question.index
        is_candidate_question = (self.election.type == self.election.TYPE_PARTY_CANDIDATE and question_index == 1)
        if is_candidate_question:
            p_list = []
        if self.election.vote_code_type == self.election.VOTE_CODE_TYPE_SHORT:
            if (self.election.security_code_length is not None and
                    self.election.security_code_length == self.election.security_code_ideal_length):
                # Decode the security code and extract the permutation indices.
                s = int(self.part.security_code[:-1])
                for index, option_count in enumerate(option_counts):
                    p_bits = (math.factorial(option_count) - 1).bit_length()
                    p = s & ((1 << p_bits) - 1)
                    if is_candidate_question and index >= question_index:
                        p_list.append(p)
                    elif index == question_index:
                        break
                    s >>= p_bits
            else:
                # Use randomness extraction to generate the question's permutation
                # index.
                def randomness_extractor(question_index, option_count):
                    key = base32.decode_to_bytes(self.part.credential)
                    msg_list = [self.ballot.serial_number, self.part.tag, question_index, 'permutation']
                    if self.election.security_code_length is not None:
                        msg_list.append(self.part.security_code)
                    msg = b','.join(force_bytes(v) for v in msg_list)
                    digest = hmac.new(key, msg, hashlib.sha256).digest()
                    return int_from_bytes(digest, byteorder='big') % math.factorial(option_count)

                if is_candidate_question:
                    for index, option_count in enumerate(option_counts[1:], start=1):
                        p_list.append(randomness_extractor(index, option_count))
                else:
                    p = randomness_extractor(question_index, option_counts[question_index])
        elif self.election.vote_code_type == self.election.VOTE_CODE_TYPE_LONG:
            # Generate a random permutation.
            if is_candidate_question:
                for option_count in option_counts[1:]:
                    p_list.append(random.randrange(math.factorial(option_count)))
            else:
                p = random.randrange(math.factorial(option_counts[question_index]))
        # Generate the permutation array from the permutation indices.
        if is_candidate_question:
            # Permute each candidate group's options according to the its
            # permutation index.
            candidate_count_per_party = option_counts[1]
            candidate_groups = []
            for index, p in enumerate(p_list):
                min_option_index = index * candidate_count_per_party
                max_option_index = min_option_index + candidate_count_per_party - 1
                option_indices = permute(range(min_option_index, max_option_index + 1), p)
                candidate_groups.append(option_indices)
            # Permute the candidate groups according to the party question's
            # permutation. A candidate group's options can be associated with
            # their party option by comparing their indices, even when the
            # options are shuffled.
            candidate_groups = [candidate_groups[i] for i in self.part.questions.all()[0].permutation]
            return list(itertools.chain.from_iterable(candidate_groups))
        else:  # party list or question-option type of election
            return permute(range(option_counts[question_index]), p)

    def generate_zk1(self):
        """
        Generate the question's ZK1 (column ZK).
        """
        self.zk1 = self._crypto['zk']

    @cached_property
    def _crypto(self):
        return crypto.ballot_gen(
            [trustee.secret_key for trustee in self.election.trustees.all()],  # trustee keys
            self.election.commitment_key,  # commitment key
            [int(not option.is_blank) for option in self.election_question.options.all()],  # option bitmask
            self.permutation,  # permutation array
            self.ballot.serial_number,  # ballot serial number
            self.part.tag,  # part tag
            self.election_question.index,  # question index
        )

    @cached_property
    def _short_vote_codes(self):
        short_vote_codes = [force_text(i) for i in range(1, self.election_question.option_count + 1)]
        random.shuffle(short_vote_codes)
        return short_vote_codes

    @cached_property
    def _long_vote_code_hash_salt(self):
        return hasher.salt()


class BallotOption(BaseBallotOption):
    vote_code = models.TextField(_("vote-code"))
    vote_code_hash = models.TextField(_("vote-code hash"), null=True, blank=True, default=None)
    commitment = JSONField(_("commitment"))
    zk1 = JSONField(_("zero-knowledge proof ZK1"))

    objects = BallotOptionManager()

    def generate_vote_code(self):
        """
        If the vote-code type is short then generate a random vote-code in
        range 1 to the number of options of this question. If the vote-code
        type is long then use the truncated Base32 encoded output of
        HMAC-SHA256 with key the part's credential and message the ballot's
        serial number, the part's tag, the question's index and the option's
        index (before the options are shuffled).
        """
        if self.election.vote_code_type == self.election.VOTE_CODE_TYPE_SHORT:
            self.vote_code = force_text(self.question._short_vote_codes[self.index])
        elif self.election.vote_code_type == self.election.VOTE_CODE_TYPE_LONG:
            key = base32.decode_to_bytes(self.part.credential)
            msg = b','.join(force_bytes(v) for v in [
                self.ballot.serial_number,
                self.part.tag,
                self.question.election_question.index,
                'vote_code',
                self.question.permutation[self.index],  # the original index
            ])
            length = self.election.vote_code_length
            digest = hmac.new(key, msg, hashlib.sha256).digest()
            self.vote_code = base32.encode_from_bytes(digest, length)[-length:]

    def generate_vote_code_hash(self):
        """
        If the vote-code type is long then generate the vote-code's hash.
        """
        if self.election.vote_code_type == self.election.VOTE_CODE_TYPE_SHORT:
            self.vote_code_hash = None
        elif self.election.vote_code_type == self.election.VOTE_CODE_TYPE_LONG:
            self.vote_code_hash = hasher.encode(self.vote_code, self.question._long_vote_code_hash_salt)

    def generate_receipt(self):
        """
        If the vote-code type is short then generate a random receipt. If the
        vote-code type is long then use the vote-code's signature as the
        receipt. In both cases, the value is Base32 encoded.
        """
        if self.election.vote_code_type == self.election.VOTE_CODE_TYPE_SHORT:
            randomness = random.getrandbits(self.election.receipt_length * 5)
            self.receipt = base32.encode(randomness, self.election.receipt_length)
        elif self.election.vote_code_type == self.election.VOTE_CODE_TYPE_LONG:
            private_key = self.election.private_key
            signature = private_key.sign(
                data=force_bytes(self.vote_code),
                padding=padding.PKCS1v15(),
                algorithm=hashes.SHA256()
            )
            self.receipt = base32.encode_from_bytes(signature, (private_key.key_size + 4) // 5)

    def generate_commitment(self):
        """
        Generate the option's commitment.
        """
        self.commitment = self._crypto[0]

    def generate_zk1(self):
        """
        Generate the option's ZK1 (row ZK).
        """
        self.zk1 = self._crypto[1]

    @cached_property
    def _crypto(self):
        return self.question._crypto['rows'][self.index]


class Administrator(BaseAdministrator):
    pass


class Trustee(BaseTrustee):
    secret_key = models.TextField(_("secret key"), null=True, blank=True, default=None)

    def generate_secret_key(self, index):
        """
        Generate the trustee's secret key.
        """
        self.secret_key = self.election._crypto[0][index]

    def send_secret_key_mail(self, connection=None):
        template_prefix = 'election_authority/emails/trustee_secret_key'
        context = {'election': self.election, 'secret_key': self.secret_key}
        return self.send_mail(template_prefix, context, connection=connection)
