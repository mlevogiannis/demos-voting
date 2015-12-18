# File: base.py

from __future__ import absolute_import, division, unicode_literals

import logging

from django.core import validators
from django.db import models
from django.db.models import Count, Max, Min
from django.utils.encoding import python_2_unicode_compatible
from django.utils.six.moves import zip
from django.utils.translation import ugettext_lazy as _

from demos.common.conf import constants
from demos.common.utils import base32cf, enums, fields

logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class Election(models.Model):
    
    # Choices definition
    
    TYPE_ELECTION = 'election'
    TYPE_REFERENDUM = 'referendum'
    
    TYPE_CHOICES = (
        (TYPE_ELECTION, _('Election')),
        (TYPE_REFERENDUM, _('Referendum')),
    )
    
    VOTECODE_TYPE_SHORT = 'short'
    VOTECODE_TYPE_LONG = 'long'
    
    VOTECODE_TYPE_CHOICES = (
        (VOTECODE_TYPE_SHORT, _('Short')),
        (VOTECODE_TYPE_LONG, _('Long')),
    )
    )
    
    # Model fields
    
    id = models.CharField(db_column='election_id', unique=True, max_length=16,
        validators=[validators.RegexValidator(regex=base32cf.re_valid)])
    
    state = fields.IntEnumField(cls=enums.State)

    type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    votecode_type = models.CharField(max_length=16, choices=VOTECODE_TYPE_CHOICES)
    
    name = models.TextField()
    
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    
    conf = models.ForeignKey('Conf', related_name='elections', related_query_name='election')
    
    # Custom methods and properties
    
    @property
    def is_election(self):
        return self.type == self.TYPE_ELECTION
    
    @property
    def is_referendum(self):
        return self.type == self.TYPE_REFERENDUM
    
    @property
    def short_votecodes(self):
        return self.type_votecodes == self.VOTECODE_TYPE_SHORT
    
    @property
    def long_votecodes(self):
        return self.type_votecodes == self.VOTECODE_TYPE_LONG
    
    @property
    def ballots_cnt(self):
        if not hasattr(self, '_ballots_cnt'):
            self._ballots_cnt = self.ballots.count()
        return self._ballots_cnt
    
    @property
    def questions_cnt(self):
        if not hasattr(self, '_questions_cnt'):
            self._questions_cnt = self.questions.count()
        return self._questions_cnt
    
    @property
    def min_options_cnt(self):
        if not hasattr(self, '_min_options_cnt'):
            q = self.questions.annotate(Count('option_c'))
            q = q.aggregate(Min('option_c__count'))
            self._min_options_cnt = q['option_c__count__min']
        return self._min_options_cnt
    
    @property
    def max_options_cnt(self):
        if not hasattr(self, '_max_options_cnt'):
            q = self.questions.annotate(Count('option_c'))
            q = q.aggregate(Max('option_c__count'))
            self._max_options_cnt = q['option_c__count__max']
        return self._max_options_cnt
    
    # Predefined methods and meta options
    
    _id = models.AutoField(db_column='id', primary_key=True)
    
    class Meta:
        abstract = True
        ordering = ['id']
    
    class ElectionManager(models.Manager):
        
        def get_by_natural_key(self, e_id):
            return self.get(id=e_id)
    
    objects = ElectionManager()
    
    def __str__(self):
        return "%s | %s" % (self.id, self.name)
    
    def natural_key(self):
        return (self.id,)
    
    natural_key.dependencies = ['%(app_label)s.Conf']
    
    def save(self, *args, **kwargs):
        self.id = base32cf.normalize(self.id)
        super(Election, self).save(*args, **kwargs)


@python_2_unicode_compatible
class Question(models.Model):
    
    election = models.ForeignKey('Election', related_name='questions', related_query_name='question')
    parts = models.ManyToManyField('Part', related_name='questions', related_query_name='question')
    
    index = models.PositiveSmallIntegerField()
    
    text = models.TextField()
    max_choices = models.PositiveSmallIntegerField()
    
    # Custom methods and properties
    
    @property
    def min_choices(self):
        return 0 if not self.election.is_referendum else 1
    
    @property
    def options_cnt(self):
        if not hasattr(self, '_options_cnt'):
            self._options_cnt = self.options_c.count()
        return self._options_cnt
    
    # Predefined methods and meta options
    
    class Meta:
        abstract = True
        ordering = ['election', 'index']
        unique_together = ['election', 'index']
    
    class QuestionManager(models.Manager):
        
        def get_by_natural_key(self, e_id, q_index):
            
            manager = Election.objects.db_manager(self.db)
            election = manager.get_by_natural_key(e_id)
            
            return self.get(election=election, index=q_index)
    
    objects = QuestionManager()
    
    def __str__(self):
        return "%s | %s" % (self.index + 1, self.text)
    
    def natural_key(self):
        return self.election.natural_key() + (self.index,)
    
    natural_key.dependencies = ['%(app_label)s.Election']


@python_2_unicode_compatible
class OptionC(models.Model):
    
    question = models.ForeignKey('Question', related_name='options_c', related_query_name='option_c')
    
    index = models.PositiveSmallIntegerField()
    text = models.TextField()
    
    # Predefined methods and meta options
    
    class Meta:
        abstract = True
        ordering = ['question', 'index']
        unique_together = ['question', 'text']
        verbose_name = 'option-candidate'
    
    class OptionCManager(models.Manager):
        
        def get_by_natural_key(self, e_id, q_index, o_index):
            
            manager = Question.objects.db_manager(self.db)
            question = manager.get_by_natural_key(e_id, q_index)
            
            return self.get(question=question, index=o_index)
    
    objects = OptionCManager()
    
    def __str__(self):
        return "%s | %s" % (self.index + 1, self.text)
    
    def natural_key(self):
        return self.question.natural_key() + (self.index,)
    
    natural_key.dependencies = ['%(app_label)s.Question']


@python_2_unicode_compatible
class Ballot(models.Model):
    
    election = models.ForeignKey('Election', related_name='ballots', related_query_name='ballot')
    serial = models.PositiveIntegerField()
    
    # Predefined methods and meta options
    
    class Meta:
        abstract = True
        ordering = ['election', 'serial']
        unique_together = ['election', 'serial']
    
    class BallotManager(models.Manager):
        
        def get_by_natural_key(self, e_id, b_serial):
            
            manager = Election.objects.db_manager(self.db)
            election = manager.get_by_natural_key(e_id)
            
            return self.get(election=election, serial=b_serial)
    
    objects = BallotManager()
    
    def __str__(self):
        return "%s" % self.serial
    
    def natural_key(self):
        return self.election.natural_key() + (self.serial,)
    
    natural_key.dependencies = ['%(app_label)s.Election']


@python_2_unicode_compatible
class Part(models.Model):
    
    # Choices definition
    
    TAG_A = 'A'
    TAG_B = 'B'
    
    TAG_CHOICES = (
        (TAG_A, 'A'),
        (TAG_B, 'B'),
    )
    
    # Model fields
    
    ballot = models.ForeignKey('Ballot', related_name='parts', related_query_name='part')
    tag = models.CharField(max_length=1, choices=TAG_CHOICES)
    
    # Predefined methods and meta options
    
    class Meta:
        abstract = True
        ordering = ['ballot', 'tag']
        unique_together = ['ballot', 'tag']
    
    class PartManager(models.Manager):
        
        def get_by_natural_key(self, e_id, b_serial, p_tag):
            
            manager = Ballot.objects.db_manager(self.db)
            ballot = manager.get_by_natural_key(e_id, b_serial)
            
            return self.get(ballot=ballot, tag=p_tag)
    
    objects = PartManager()
    
    def __str__(self):
        return "%s" % self.tag
    
    def natural_key(self):
        return self.ballot.natural_key() + (self.tag,)
    
    natural_key.dependencies = ['%(app_label)s.Ballot']
    
    def save(self, *args, **kwargs):
        self.tag = self.tag.upper()
        super(Part, self).save(*args, **kwargs)


@python_2_unicode_compatible
class OptionV(models.Model):
    
    part = models.ForeignKey('Part', related_name='options', related_query_name='option')
    question = models.ForeignKey('Question', related_name='options_v', related_query_name='option_v')
    
    index = models.PositiveSmallIntegerField()
    
    # Predefined methods and meta options
    
    class Meta:
        abstract = True
        ordering = ['part', 'question', 'index']
        unique_together = ['part', 'question', 'index']
        verbose_name = 'option-votecode'
    
    class OptionVManager(models.Manager):
        
        def get_by_natural_key(self, e_id, b_serial, p_tag, q_index, o_index):
            
            manager = Part.objects.db_manager(self.db)
            part = manager.get_by_natural_key(e_id, b_serial, p_tag)
            
            manager = Question.objects.db_manager(self.db)
            question = manager.get_by_natural_key(e_id, q_index)
            
            return self.get(part=part, question=question, index=o_index)
    
    objects = OptionVManager()
    
    def __str__(self):
        return "%s" % (self.index + 1)
    
    def natural_key(self):
        return self.part.natural_key() + self.question.natural_key()[1:] + (self.index,)
    
    natural_key.dependencies = ['%(app_label)s.Part', '%(app_label)s.Question']


@python_2_unicode_compatible
class Trustee(models.Model):
    
    election = models.ForeignKey('Election', related_name='trustees', related_query_name='trustee')
    email = models.EmailField()
    
    # Predefined methods and meta options
    
    class Meta:
        abstract = True
        unique_together = ['election', 'email']
    
    class TrusteeManager(models.Manager):
        
        def get_by_natural_key(self, e_id, t_email):
            
            manager = Election.objects.db_manager(self.db)
            election = manager.get_by_natural_key(e_id)
            
            return self.get(election=election, email=t_email)
    
    objects = TrusteeManager()
    
    def __str__(self):
        return "%s" % self.email
    
    def natural_key(self):
        return self.election.natural_key() + (self.email,)
    
    natural_key.dependencies = ['%(app_label)s.Election']


@python_2_unicode_compatible
class Conf(models.Model):
    
    # Choices definition
    
    VERSION_1 = '1'
    
    VERSION_CHOICES = (
        (VERSION_1, '1'),
    )
    
    # Model fields
    
    version = models.CharField(max_length=4, choices=VERSION_CHOICES, default=VERSION_1)
    
    receipt_len = models.PositiveSmallIntegerField(default=constants.RECEIPT_LEN)
    votecode_len = models.PositiveSmallIntegerField(default=constants.VOTECODE_LEN)
    security_code_len = models.PositiveSmallIntegerField(default=constants.SECURITY_CODE_LEN)
    
    credential_bits = models.PositiveSmallIntegerField(default=constants.CREDENTIAL_BITS)
    
    hmac_alg = models.CharField(max_length=32, default=constants.HMAC_ALG)
    hasher_alg = models.CharField(max_length=32, default=constants.HASHER_ALG)
    
    rsa_pkey_bits = models.PositiveSmallIntegerField(default=constants.RSA_PKEY_BITS)
    rsa_signature_alg = models.CharField(max_length=32, default=constants.RSA_SIGNATURE_ALG)
    
    ecc_curve = models.PositiveSmallIntegerField(default=constants.ECC_CURVE)
    
    # Custom methods and properties
    
    @classmethod
    def defaults(cls):
        kwargs = {}
        for field in cls._meta.get_fields():
            if not (field.auto_created or field.is_relation):
                kwargs[field.name] = field.default
        return kwargs
    
    # Predefined methods and meta options
    
    class Meta:
        abstract = True
        unique_together = ['version', 'receipt_len', 'votecode_len', 'security_code_len', 'credential_bits',
                           'hmac_alg', 'hasher_alg', 'rsa_pkey_bits', 'rsa_signature_alg', 'ecc_curve']
    
    class ConfManager(models.Manager):
        
        def get_by_natural_key(self, *args, **kwargs):
            
            fields = self.model._meta.unique_together[0]
            kwargs.update(dict(zip(fields, args)))
            
            return self.get(**kwargs)
    
    objects = ConfManager()
    
    def __str__(self):
        return "%s" % self.version
    
    def natural_key(self):
        return tuple([getattr(self, name) for name in self._meta.unique_together[0]])


@python_2_unicode_compatible
class Task(models.Model):
    
    task_id = models.UUIDField(unique=True)
    election = models.ForeignKey('Election', related_name='tasks', related_query_name='task')
    
    # Predefined methods and meta options
    
    class Meta:
        abstract = True
    
    def __str__(self):
        return "%s | %s" % (self.election.id, self.task_id)

