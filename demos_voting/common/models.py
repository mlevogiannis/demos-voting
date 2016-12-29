# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib
import hmac
import itertools
import logging
import math

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import six
from django.utils.encoding import force_bytes, force_text, python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.six.moves import range, zip
from django.utils.translation import pgettext_lazy, ugettext_lazy as _

from demos_voting.common import managers
from demos_voting.common.utils import base32
from demos_voting.common.utils.int import int_from_bytes
from demos_voting.common.utils.permutation import permutation

logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class Election(models.Model):

    TYPE_REFERENDUM = 'referendum'
    TYPE_ELECTION = 'election'

    TYPE_CHOICES = (
        (TYPE_REFERENDUM, pgettext_lazy("type", "Referendum")),
        (TYPE_ELECTION, pgettext_lazy("type", "Election")),
    )

    VOTECODE_TYPE_SHORT = 'short'
    VOTECODE_TYPE_LONG = 'long'

    VOTECODE_TYPE_CHOICES = (
        (VOTECODE_TYPE_SHORT, _("Short")),
        (VOTECODE_TYPE_LONG, _("Long")),
    )

    SECURITY_CODE_TYPE_NONE = 'none'
    SECURITY_CODE_TYPE_NUMERIC = 'numeric'
    SECURITY_CODE_TYPE_ALPHANUMERIC = 'alphanumeric'

    SECURITY_CODE_TYPE_CHOICES = (
        (SECURITY_CODE_TYPE_NONE, _("None")),
        (SECURITY_CODE_TYPE_NUMERIC, _("Numeric")),
        (SECURITY_CODE_TYPE_ALPHANUMERIC, _("Alphanumeric")),
    )

    SECURITY_CODE_MIN_LENGTH = 1
    SECURITY_CODE_MAX_LENGTH = 8

    STATE_DRAFT = 'draft'
    STATE_PENDING = 'pending'
    STATE_SETUP_STARTED = 'setup_started'
    STATE_SETUP_ENDED = 'setup_ended'
    STATE_BALLOT_DISTRIBUTION_STARTED = 'ballot_distribution_started'
    STATE_BALLOT_DISTRIBUTION_ENDED = 'ballot_distribution_ended'
    STATE_VOTING_STARTED = 'voting_started'
    STATE_VOTING_ENDED = 'voting_ended'
    STATE_TALLYING_STARTED = 'tallying_started'
    STATE_TALLYING_ENDED = 'tallying_ended'
    STATE_COMPLETED = 'completed'
    STATE_FAILED = 'failed'
    STATE_CANCELLED = 'cancelled'

    STATE_CHOICES = (
        (STATE_DRAFT, _("Draft")),
        (STATE_PENDING, _("Pending")),
        (STATE_SETUP_STARTED, _("Setup started")),
        (STATE_SETUP_ENDED, _("Setup ended")),
        (STATE_BALLOT_DISTRIBUTION_STARTED, _("Ballot distribution started")),
        (STATE_BALLOT_DISTRIBUTION_ENDED, _("Ballot distribution ended")),
        (STATE_VOTING_STARTED, _("Voting started")),
        (STATE_VOTING_ENDED, _("Voting ended")),
        (STATE_TALLYING_STARTED, _("Tallying started")),
        (STATE_TALLYING_ENDED, _("Tallying ended")),
        (STATE_COMPLETED, _("Completed")),
        (STATE_FAILED, _("Failed")),
        (STATE_CANCELLED, _("Cancelled")),
    )

    DEFAULT_HASHER_IDENTIFIER = 'pbkdf2-sha512'

    id = models.CharField(_("id"), unique=True, max_length=16, db_column='_id',
        validators=[RegexValidator(regex=(r'^%s+$' % base32.regex))])

    name = models.TextField(_("name"))

    voting_starts_at = models.DateTimeField(_("voting starts at"))
    voting_ends_at = models.DateTimeField(_("voting ends at"))

    state = models.CharField(_("state"), max_length=64, choices=STATE_CHOICES)

    type = models.CharField(_("type"), max_length=16, choices=TYPE_CHOICES)
    votecode_type = models.CharField(_("vote-code type"), max_length=16, choices=VOTECODE_TYPE_CHOICES)
    security_code_type = models.CharField(_("security code type"), max_length=16, choices=SECURITY_CODE_TYPE_CHOICES)

    ballot_count = models.PositiveIntegerField(_("number of ballots"))

    credential_length = models.PositiveSmallIntegerField(_("credential length"), default=26)
    long_votecode_length = models.PositiveSmallIntegerField(_("long votecode length"), null=True, default=16)
    receipt_length = models.PositiveSmallIntegerField(_("receipt length"), default=8)
    security_code_length = models.PositiveSmallIntegerField(_("security code length"), null=True)

    curve_name = models.CharField(_("elliptic curve name"), max_length=16, default='prime256v1')

    _id = models.AutoField(primary_key=True, db_column='id')

    # Custom methods and properties

    @property
    def type_is_referendum(self):
        return self.type == self.TYPE_REFERENDUM

    @property
    def type_is_election(self):
        return self.type == self.TYPE_ELECTION

    @property
    def votecode_type_is_short(self):
        return self.votecode_type == self.VOTECODE_TYPE_SHORT

    @property
    def votecode_type_is_long(self):
        return self.votecode_type == self.VOTECODE_TYPE_LONG

    @property
    def security_code_type_is_none(self):
        return self.security_code_type == self.SECURITY_CODE_TYPE_NONE

    @property
    def security_code_type_is_numeric(self):
        return self.security_code_type == self.SECURITY_CODE_TYPE_NUMERIC

    @property
    def security_code_type_is_alphanumeric(self):
        return self.security_code_type == self.SECURITY_CODE_TYPE_ALPHANUMERIC

    @cached_property
    def _security_code_length(self):
        optionss = (question.options.all() for question in self.questions.all())
        return self._generate_security_code_length(optionss)

    def _generate_security_code_length(self, optionss):
        groups = [len(options) for options in optionss]
        if self.type_is_election:
            groups = [groups[0]] + [groups[1] // groups[0]] * groups[0]

        # Calculate the security code's ideal length, the one required to
        # encode all possible permutation indices for all option groups.

        s_max=0
        for group_len in groups:
            s_max |= ((math.factorial(group_len) - 1) << s_max.bit_length())

        if self.security_code_type_is_numeric:
            security_code = force_text(s_max)
        elif self.security_code_type_is_alphanumeric:
            security_code = base32.encode(s_max)

        return len(security_code)

    # Default manager, meta options and natural key

    objects = managers.ElectionManager()

    class Meta:
        abstract = True
        default_related_name = 'elections'
        ordering = ['id']
        verbose_name = pgettext_lazy("model", "election")
        verbose_name_plural = pgettext_lazy("model", "elections")

    def natural_key(self):
        return (self.id,)

    def __str__(self):
        return "%s - %s" % (self.id, self.name)


@python_2_unicode_compatible
class Question(models.Model):

    LAYOUT_ONE_COLUMN = 'one_column'
    LAYOUT_TWO_COLUMN = 'two_column'

    LAYOUT_CHOICES = (
        (LAYOUT_ONE_COLUMN, _("One-column")),
        (LAYOUT_TWO_COLUMN, _("Two-column")),
    )

    election = models.ForeignKey('Election')

    index = models.PositiveSmallIntegerField(_("index"))
    name = models.TextField(_("name"), null=True)

    min_choices = models.PositiveSmallIntegerField(_("minimum number of choices"))
    max_choices = models.PositiveSmallIntegerField(_("maximum number of choices"))

    layout = models.CharField(_("layout"), max_length=16, choices=LAYOUT_CHOICES)

    # Custom methods and properties

    @property
    def layout_is_one_column(self):
        return self.layout == self.LAYOUT_ONE_COLUMN

    @property
    def layout_is_two_column(self):
        return self.layout == self.LAYOUT_TWO_COLUMN

    # Default manager, meta options and natural key

    objects = managers.QuestionManager()

    class Meta:
        abstract = True
        default_related_name = 'questions'
        ordering = ['election', 'index']
        unique_together = ['election', 'index']
        verbose_name = _("question")
        verbose_name_plural = _("questions")

    def natural_key(self):
        return self.election.natural_key() + (self.index,)

    natural_key.dependencies = ['Election']

    def __str__(self):
        return "%s - %s" % (self.index + 1, self.name)


@python_2_unicode_compatible
class Option(models.Model):

    question = models.ForeignKey('Question')

    index = models.PositiveSmallIntegerField(_("index"))
    name = models.TextField(_("name"), null=True)

    # Custom methods and properties

    @property
    def is_blank(self):
        return self.name is None

    # Related object access

    @cached_property
    def election(self):
        return self.question.election

    # Default manager, meta options and natural key

    objects = managers.OptionManager()

    class Meta:
        abstract = True
        default_related_name = 'options'
        ordering = ['question', 'index']
        unique_together = ['question', 'index']
        verbose_name = _("option")
        verbose_name_plural = _("options")

    def natural_key(self):
        return self.question.natural_key() + (self.index,)

    natural_key.dependencies = ['Question']

    def __str__(self):
        return "%s - %s" % (self.index + 1, self.name)


@python_2_unicode_compatible
class Ballot(models.Model):

    election = models.ForeignKey('Election')
    serial_number = models.PositiveIntegerField(_("serial number"))

    # Default manager, meta options and natural key

    objects = managers.BallotManager()

    class Meta:
        abstract = True
        default_related_name = 'ballots'
        ordering = ['election', 'serial_number']
        unique_together = ['election', 'serial_number']
        verbose_name = _("ballot")
        verbose_name_plural = _("ballots")

    def natural_key(self):
        return self.election.natural_key() + (self.serial_number,)

    natural_key.dependencies = ['Election']

    def __str__(self):
        return "%s" % self.serial_number


@python_2_unicode_compatible
class Part(models.Model):

    TAG_A = 'A'
    TAG_B = 'B'

    TAG_CHOICES = (
        (TAG_A, 'A'),
        (TAG_B, 'B'),
    )

    ballot = models.ForeignKey('Ballot')
    tag = models.CharField(_("tag"), max_length=1, choices=TAG_CHOICES)

    # Related object access

    @cached_property
    def election(self):
        return self.ballot.election

    # Default manager, meta options and natural key

    objects = managers.PartManager()

    class Meta:
        abstract = True
        default_related_name = 'parts'
        ordering = ['ballot', 'tag']
        unique_together = ['ballot', 'tag']
        verbose_name = _("part")
        verbose_name_plural = _("parts")

    def natural_key(self):
        return self.ballot.natural_key() + (self.tag,)

    natural_key.dependencies = ['Ballot']

    def __str__(self):
        return "%s" % self.tag


@python_2_unicode_compatible
class PQuestion(models.Model):

    part = models.ForeignKey('Part')
    question = models.ForeignKey('Question')

    # Custom methods and properties

    @cached_property
    def index(self):
        return self.question.index

    @cached_property
    def permutation(self):
        if self.election.type_is_election:
            # The first group is always the party list, followed by one group
            # for each party's candidates. The candidate list has a special
            # structure by grouping together the options that correspond to
            # each party's candidates. All parties always have the same number
            # of candidates, which includes the blank ones.

            party_count = self.election.questions.all()[0].options.count()
            candidate_count = self.election.questions.all()[1].options.count()

            groups = [tuple(range(party_count))] + [
                group for group in zip(*([iter(range(candidate_count))] * (candidate_count // party_count)))
            ]

        elif self.election.type_is_referendum:
            groups = [tuple(range(questions.options.count())) for questions in self.election.questions.all()]

        question_is_candidate_list = (self.election.type_is_election and self.index == 1)

        if question_is_candidate_list:
            p_list = []

        # Check whether the security code has enough bits to encode the
        # permutations for all groups.

        if self.election.security_code_length >= self.election._security_code_length:
            # Decode the security code to get the group's permutation.

            if self.election.security_code_type_is_numeric:
                s = int(self.part.security_code)
            elif self.election.security_code_type_is_alphanumeric:
                s = base32.decode(self.part.security_code)

            for i, group in enumerate(groups):
                p_bits = (math.factorial(len(group)) - 1).bit_length()
                p = s & ((1 << p_bits) - 1)
                if question_is_candidate_list:
                    p_list.append(p)
                elif i == self.index:
                    break
                s >>= p_bits
        else:
            # Use the randomness extractor to generate the group's permutation.

            def _randomness_extractor(i, group):
                serial_number = force_text(self.ballot.serial_number)
                group_index = force_text(i).zfill(len(force_text(len(group) - 1)))
                key = self.ballot.credential + self.part.security_code
                msg = serial_number + self.part.tag + group_index
                digest = hmac.new(force_bytes(key), force_bytes(msg), hashlib.sha512).digest()
                return int_from_bytes(digest, byteorder='big') % math.factorial(len(group))

            if question_is_candidate_list:
                for i, group in enumerate(groups):
                    p_list.append(_randomness_extractor(i, group))
            else:
                p = _randomness_extractor(self.index, groups[self.index])

        # Create the permutation array.

        if question_is_candidate_list:
            permutation_array = itertools.chain.from_iterable(
                permutation([permutation(group, p) for group, p in zip(groups[1:], p_list[1:])], p_list[0])
            )
        else:
            permutation_array = permutation(groups[self.index], p)

        return list(permutation_array)

    # Related object access

    @cached_property
    def election(self):
        return self.ballot.election

    @cached_property
    def ballot(self):
        return self.part.ballot

    # Default manager, meta options and natural key

    objects = managers.PQuestionManager()

    class Meta:
        abstract = True
        default_related_name = 'questions'
        ordering = ['part', 'question']
        unique_together = ['part', 'question']

    def natural_key(self):
        return self.part.natural_key() + self.question.natural_key()[1:]

    natural_key.dependencies = ['Part', 'Question']

    def __str__(self):
        return "%s - %s" % (self.part.tag, self.question.index + 1)


@python_2_unicode_compatible
class POption(models.Model):

    question = models.ForeignKey('PQuestion')
    index = models.PositiveSmallIntegerField(_("index"))

    # Related object access

    @cached_property
    def election(self):
        return self.ballot.election

    @cached_property
    def ballot(self):
        return self.part.ballot

    @cached_property
    def part(self):
        return self.question.part

    # Default manager, meta options and natural key

    objects = managers.POptionManager()

    class Meta:
        abstract = True
        default_related_name = 'options'
        ordering = ['question', 'index']
        unique_together = ['question', 'index']
        verbose_name = _("option")
        verbose_name_plural = _("options")

    def natural_key(self):
        return self.question.natural_key() + (self.index,)

    natural_key.dependencies = ['PQuestion']

    def __str__(self):
        return "%s" % (self.index + 1)


@python_2_unicode_compatible
class Task(models.Model):

    election = models.ForeignKey('Election')

    name = models.CharField(_("name"), max_length=128)
    id = models.UUIDField(_("id"), unique=True, db_column='_id')

    _id = models.AutoField(primary_key=True, db_column='id')

    # Default manager, meta options and natural key

    objects = managers.TaskManager()

    class Meta:
        abstract = True
        default_related_name = 'tasks'
        ordering = ['election', 'name']
        unique_together = ['election', 'name']
        verbose_name = _("task")
        verbose_name_plural = _("tasks")

    def natural_key(self):
        return self.election.natural_key() + (self.id,)

    def __str__(self):
        return "%s - %s" % (self.election.id, self.id)


@python_2_unicode_compatible
class PrivateApiUser(models.Model):

    APP_DEPENDENCIES = {
        'ea':  ['bds', 'abb', 'vbb'],
        'bds': ['ea'],
        'abb': ['ea', 'vbb'],
        'vbb': ['ea', 'abb'],
    }

    APP_LABEL_CHOICES = (
        ('ea',  _("Election Authority")),
        ('bds', _("Ballot Distribution Server")),
        ('abb', _("Audit Bulletin Board")),
        ('vbb', _("Virtual Ballot Box")),
    )

    app_label = models.CharField(_("application label"), max_length=4, unique=True, choices=APP_LABEL_CHOICES)
    preshared_key = models.CharField(_("pre-shared-key"), max_length=128)

    # Default manager, meta options and natural key

    objects = managers.PrivateApiUserManager()

    class Meta:
        abstract = True
        default_related_name = 'users'
        verbose_name = _("private API user")
        verbose_name_plural = _("private API user")

    def natural_key(self):
        return (self.app_label,)

    def __str__(self):
        return "%s" % self.app_label


@python_2_unicode_compatible
class PrivateApiNonce(models.Model):

    TYPE_LOCAL = 'local'
    TYPE_REMOTE = 'remote'

    TYPE_CHOICES = (
        (TYPE_LOCAL, _("local")),
        (TYPE_REMOTE, _("remote")),
    )

    user = models.ForeignKey('PrivateApiUser')

    nonce = models.CharField(_("nonce"), max_length=32)
    timestamp = models.BigIntegerField(_("timestamp"))

    type = models.CharField(_("type"), max_length=8, choices=TYPE_CHOICES)

    # Default manager, meta options and natural key

    objects = managers.PrivateApiNonceManager()

    class Meta:
        abstract = True
        default_related_name = 'nonces'
        unique_together = ['user', 'nonce', 'timestamp', 'type']
        verbose_name = _("private API nonce")
        verbose_name_plural = _("private API nonce")

    def natural_key(self):
        return self.user.natural_key() + (self.nonce, self.timestamp, self.type)

    def __str__(self):
        return "%s - %s - %s" % (self.nonce, self.timestamp, self.type)
