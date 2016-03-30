# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib
import hmac
import logging

from django.core.validators import RegexValidator
from django.db import models
from django.utils import six
from django.utils.encoding import force_bytes, python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.six.moves import range, zip
from django.utils.translation import pgettext_lazy, ugettext_lazy as _

from demos.common import fields, managers
from demos.common.hashers import get_hasher
from demos.common.utils import base32

logger = logging.getLogger(__name__)


# ----------------------- #
#                         #
#        Election         #
#       ___/  \           #
#      /       \          #
#   Ballot      \         #
#     |          \        #
#     |           \       #
#   Part        Question  #
#     |     ___/   |      #
#     |    /       |      #
#  Option_C     Option_P  #
#                         #
# ----------------------- #


@python_2_unicode_compatible
class Election(models.Model):
    
    TYPE_ELECTION = 'election'
    TYPE_REFERENDUM = 'referendum'
    
    TYPE_CHOICES = (
        (TYPE_ELECTION, pgettext_lazy("type", "Election")),
        (TYPE_REFERENDUM, pgettext_lazy("type", "Referendum")),
    )
    
    VOTECODE_TYPE_SHORT = 'short'
    VOTECODE_TYPE_LONG = 'long'
    
    VOTECODE_TYPE_CHOICES = (
        (VOTECODE_TYPE_SHORT, _("Short")),
        (VOTECODE_TYPE_LONG, _("Long")),
    )
    
    STATE_DRAFT = 'draft'
    STATE_PENDING = 'pending'
    STATE_SETUP_STARTED = 'setup_started'
    STATE_SETUP_ENDED = 'setup_ended'
    STATE_BALLOT_DISTRIBUTION_STARTED = 'ballot_distribution_started'
    STATE_BALLOT_DISTRIBUTION_SUSPENDED = 'ballot_distribution_suspended'
    STATE_BALLOT_DISTRIBUTION_ENDED = 'ballot_distribution_ended'
    STATE_VOTING_STARTED = 'voting_started'
    STATE_VOTING_SUSPENDED = 'voting_suspended'
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
        (STATE_BALLOT_DISTRIBUTION_SUSPENDED, _("Ballot distribution suspended")),
        (STATE_BALLOT_DISTRIBUTION_ENDED, _("Ballot distribution ended")),
        (STATE_VOTING_STARTED, _("Voting started")),
        (STATE_VOTING_SUSPENDED, _("Voting suspended")),
        (STATE_VOTING_ENDED, _("Voting ended")),
        (STATE_TALLYING_STARTED, _("Tallying started")),
        (STATE_TALLYING_ENDED, _("Tallying ended")),
        (STATE_COMPLETED, _("Completed")),
        (STATE_FAILED, _("Failed")),
        (STATE_CANCELLED, _("Cancelled")),
    )
    
    id = models.CharField(_("id"), unique=True, max_length=16, db_column='_id',
        validators=[RegexValidator(regex=(r'^%s+$' % base32.regex))])
    
    name = models.TextField(_("name"))
    
    ballot_distribution_starts_at = models.DateTimeField(_("ballot distribution starts at"))
    ballot_distribution_ends_at = models.DateTimeField(_("ballot distribution ends at"))
    voting_starts_at = models.DateTimeField(_("voting starts at"))
    voting_ends_at = models.DateTimeField(_("voting ends at"))
    
    state = models.CharField(_("state"), max_length=64, choices=STATE_CHOICES)

    type = models.CharField(_("type"), max_length=16, choices=TYPE_CHOICES)
    votecode_type = models.CharField(_("vote-code type"), max_length=16, choices=VOTECODE_TYPE_CHOICES)
    
    ballot_cnt = models.PositiveIntegerField(_("number of ballots"))
    question_cnt = models.PositiveSmallIntegerField(_("number of questions"))
    
    _conf = fields.JSONField(db_column='conf', default={
        'credential_bits': 64,
        'long_votecode_len': 16,
        'receipt_len': 10,
        'security_code_len': 8,
        'hash_algorithm': 'sha256',
    })
    
    _id = models.AutoField(db_column='id', primary_key=True)
    
    # Custom methods and properties
    
    @property
    def type_is_election(self):
        return self.type == self.TYPE_ELECTION
    
    @property
    def type_is_referendum(self):
        return self.type == self.TYPE_REFERENDUM
    
    @property
    def votecode_type_is_short(self):
        return self.votecode_type == self.VOTECODE_TYPE_SHORT
    
    @property
    def votecode_type_is_long(self):
        return self.votecode_type == self.VOTECODE_TYPE_LONG
    
    @cached_property
    def conf(self):
        return type(str('Conf'), (object,), self._conf)()
    
    @cached_property
    def hasher(self):
        return get_hasher(self.conf)
    
    # Default manager, meta options and natural key
    
    objects = managers.ElectionManager()
    
    class Meta:
        abstract = True
        default_related_name = 'elections'
        ordering = ['id']
        verbose_name = pgettext_lazy("process", "election")
        verbose_name_plural = pgettext_lazy("process", "elections")
    
    def natural_key(self):
        return (self.id,)
    
    natural_key.dependencies = ['Conf']
    
    def __str__(self):
        return "%s - %s" % (self.id, self.name)


@python_2_unicode_compatible
class Ballot(models.Model):
    
    election = models.ForeignKey('Election')
    serial = models.PositiveIntegerField(_("serial number"))
    
    # Related object access
    
    @cached_property
    def conf(self):
        return self.election.conf
    
    # Default manager, meta options and natural key
    
    objects = managers.BallotManager()
    
    class Meta:
        abstract = True
        default_related_name = 'ballots'
        ordering = ['election', 'serial']
        unique_together = ['election', 'serial']
        verbose_name = _("ballot")
        verbose_name_plural = _("ballots")
    
    def natural_key(self):
        return self.election.natural_key() + (self.serial,)
    
    natural_key.dependencies = ['Election']
    
    def __str__(self):
        return "%s" % self.serial


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
    
    @cached_property
    def conf(self):
        return self.election.conf
    
    @property
    def questions(self):
        manager = self._questions
        manager._annotate_with_related_pk(self)
        return manager
    
    # Default manager, meta options and natural key
    
    objects = managers.PartManager()
    
    class Meta:
        abstract = True
        default_related_name = 'parts'
        ordering = ['ballot', 'tag']
        unique_together = ['ballot', 'tag']
        verbose_name = _("sheet")
        verbose_name_plural = _("sheets")
    
    def natural_key(self):
        return self.ballot.natural_key() + (self.tag,)
    
    natural_key.dependencies = ['Ballot']
    
    def __str__(self):
        return "%s" % self.tag


@python_2_unicode_compatible
class Question(models.Model):
    
    LAYOUT_ONE_COLUMN = 'one_column'
    LAYOUT_TWO_COLUMN = 'two_column'
    
    LAYOUT_CHOICES = (
        (LAYOUT_ONE_COLUMN, _("One-column")),
        (LAYOUT_TWO_COLUMN, _("Two-column")),
    )
    
    election = models.ForeignKey('Election')
    parts = models.ManyToManyField('Part', through='PartQuestion', related_name='_questions')
    
    index = models.PositiveSmallIntegerField(_("index"))
    text = models.TextField(_("question"))
    layout = models.CharField(_("layout"), max_length=16, choices=LAYOUT_CHOICES)
    option_cnt = models.PositiveSmallIntegerField(_("number of options"))
    max_choices = models.PositiveSmallIntegerField(_("maximum number of choices"))
    
    # Custom methods and properties
    
    @property
    def min_choices(self):
        return 0 if not self.election.type_is_referendum else 1
    
    # Related object access
    
    @cached_property
    def conf(self):
        return self.election.conf
    
    @property
    def options(self):
        if hasattr(self, '_related_part_pk'):
            raise AttributeError
        return self.options_p
    
    @property
    def options_c(self):
        if not hasattr(self, '_related_part_pk'):
            raise AttributeError
        return self.partquestions.get(part=self._related_part_pk).options_c
    
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
        return "%s - %s" % (self.index + 1, self.text)


@python_2_unicode_compatible
class Option_P(models.Model):
    
    question = models.ForeignKey('Question')
    
    index = models.PositiveSmallIntegerField(_("index"))
    text = models.TextField(_("option"))
    
    # Related object access
    
    @cached_property
    def election(self):
        return self.question.election
    
    @cached_property
    def conf(self):
        return self.election.conf
    
    # Default manager, meta options and natural key
    
    objects = managers.OptionManager_P()
    
    class Meta:
        abstract = True
        default_related_name = 'options_p'
        ordering = ['question', 'index']
        unique_together = ['question', 'text']
        verbose_name = _("option")
        verbose_name_plural = _("options")
    
    def natural_key(self):
        return self.question.natural_key() + (self.index,)
    
    natural_key.dependencies = ['Question']
    
    def __str__(self):
        return "%s - %s" % (self.index + 1, self.text)


@python_2_unicode_compatible
class Option_C(models.Model):
    
    partquestion = models.ForeignKey('PartQuestion')
    index = models.PositiveSmallIntegerField(_("index"))
    
    # Custom methods and properties
    
    @property
    def votecode_hash(self):
        
        value = self.votecode_hash_value
        
        if not value:
            return value
        
        salt = self.partquestion.votecode_hash_salt
        params = self.partquestion.votecode_hash_params
        
        return self.election.hasher.join(params, salt, value)
    
    def _generate_long_votecode(self):
        
        key = "%s" % (self.part.security_code,)
        
        option_index = six.text_type(self.index).zfill(len(six.text_type(self.question.option_cnt - 1)))
        question_index = six.text_type(self.question.index).zfill(len(six.text_type(self.election.question_cnt - 1)))
        
        msg = "%s%s%s" % (self.ballot.credential, question_index, option_index)
        
        digestmod = getattr(hashlib, self.conf.hash_algorithm)
        digest = hmac.new(force_bytes(key), force_bytes(msg), digestmod).digest()
        long_votecode_len = self.conf.long_votecode_len
        long_votecode = base32.encode_from_bytes(digest, long_votecode_len)[-long_votecode_len:]
        
        return long_votecode
    
    # Related object access
    
    @cached_property
    def election(self):
        return self.question.election
    
    @cached_property
    def ballot(self):
        return self.part.ballot
    
    @cached_property
    def part(self):
        return self.partquestion.part
    
    @cached_property
    def question(self):
        return self.partquestion.question
    
    @cached_property
    def conf(self):
        return self.election.conf
    
    # Default manager, meta options and natural key
    
    objects = managers.OptionManager_C()
    
    class Meta:
        abstract = True
        default_related_name = 'options_c'
        ordering = ['partquestion', 'index']
        unique_together = ['partquestion', 'index']
        verbose_name = _("option")
        verbose_name_plural = _("options")
    
    def natural_key(self):
        return self._partquestion.natural_key() + (self.index,)
    
    natural_key.dependencies = ['PartQuestion']
    
    def __str__(self):
        return "%s" % (self.index + 1)


@python_2_unicode_compatible
class PartQuestion(models.Model):
    
    part = models.ForeignKey('Part')
    question = models.ForeignKey('Question')
    
    # Related object access
    
    @cached_property
    def election(self):
        return self.question.election
    
    @cached_property
    def ballot(self):
        return self.part.ballot
    
    @cached_property
    def conf(self):
        return self.election.conf
    
    # Default manager, meta options and natural key
    
    objects = managers.PartQuestionManager()
    
    class Meta:
        abstract = True
        default_related_name = 'partquestions'
        ordering = ['part', 'question']
        unique_together = ['part', 'question']
    
    def natural_key(self):
        return self.part.natural_key() + self.question.natural_key()[1:]
    
    natural_key.dependencies = ['Part', 'Question']
    
    def __str__(self):
        return "%s - %s" % (self.part.tag, self.question.index + 1)


@python_2_unicode_compatible
class Task(models.Model):
    
    task_id = models.UUIDField(_("id"), unique=True)
    election = models.ForeignKey('Election')
    
    # Default manager, meta options and natural key
    
    objects = managers.TaskManager()
    
    class Meta:
        abstract = True
        default_related_name = 'tasks'
        verbose_name = _("task")
        verbose_name_plural = _("tasks")
    
    def natural_key(self):
        return self.election.natural_key() + (self.task_id,)
    
    def __str__(self):
        return "%s - %s" % (self.election.id, self.task_id)

