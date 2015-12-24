# File: base.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from django.core import validators
from django.db import models
from django.db.models import Count, Max, Min
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.six.moves import zip
from django.utils.translation import ugettext_lazy as _

from demos.common.conf import constants
from demos.common.hashers import get_hasher
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
    
    _id = models.AutoField(db_column='id', primary_key=True)
    
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
    
    @cached_property
    def ballots_cnt(self):
        return self.ballots.count()
    
    @cached_property
    def questions_cnt(self):
        return self.questions.count()
    
    @cached_property
    def min_options_cnt(self):
        q = self.questions.annotate(Count('option_c'))
        q = q.aggregate(Min('option_c__count'))
        return q['option_c__count__min']
    
    @cached_property
    def max_options_cnt(self):
        q = self.questions.annotate(Count('option_c'))
        q = q.aggregate(Max('option_c__count'))
        return q['option_c__count__max']
    
    class Meta:
        abstract = True
        ordering = ['id']
    
    class Manager(models.Manager):
        
        def get_by_natural_key(self, e_id):
            return self.get(id=e_id)
    
    objects = Manager()
    
    def __str__(self):
        return "%s | %s" % (self.id, self.name)
    
    def natural_key(self):
        return (self.id,)
    
    natural_key.dependencies = ['Conf']
    
    def save(self, *args, **kwargs):
        self.id = base32cf.normalize(self.id)
        super(Election, self).save(*args, **kwargs)


@python_2_unicode_compatible
class QuestionC(models.Model):
    
    election = models.ForeignKey('Election', related_name='questions', related_query_name='question')
    
    text = models.TextField()
    index = models.PositiveSmallIntegerField()
    
    max_choices = models.PositiveSmallIntegerField()
    
    # Custom methods and properties
    
    @property
    def min_choices(self):
        return 0 if not self.election.is_referendum else 1
    
    @cached_property
    def options_cnt(self):
        return self.options_c.count()
    
    class Meta:
        abstract = True
        ordering = ['election', 'index']
        unique_together = ['election', 'index']
    
    class Manager(models.Manager):
        
        def get_by_natural_key(self, e_id, q_index):
            
            manager = Election.objects.db_manager(self.db)
            election = manager.get_by_natural_key(e_id)
            
            return self.get(election=election, index=q_index)
    
    objects = Manager()
    
    def __str__(self):
        return "%s | %s" % (self.index + 1, self.text)
    
    def natural_key(self):
        return self.election.natural_key() + (self.index,)
    
    natural_key.dependencies = ['Election']


@python_2_unicode_compatible
class OptionC(models.Model):
    
    question = models.ForeignKey('QuestionC', related_name='options', related_query_name='option')
    
    index = models.PositiveSmallIntegerField()
    text = models.TextField()
    
    class Meta:
        abstract = True
        ordering = ['question', 'index']
        unique_together = ['question', 'text']
    
    class Manager(models.Manager):
        
        def get_by_natural_key(self, e_id, q_index, o_index):
            
            manager = QuestionC.objects.db_manager(self.db)
            question = manager.get_by_natural_key(e_id, q_index)
            
            return self.get(question=question, index=o_index)
    
    objects = Manager()
    
    def __str__(self):
        return "%s | %s" % (self.index + 1, self.text)
    
    def natural_key(self):
        return self.question.natural_key() + (self.index,)
    
    natural_key.dependencies = ['QuestionC']


@python_2_unicode_compatible
class Ballot(models.Model):
    
    election = models.ForeignKey('Election', related_name='ballots', related_query_name='ballot')
    serial = models.PositiveIntegerField()
    
    # Custom methods and properties
    
    @property
    def is_cast(self):
        return self.cast_at is not None
    
    def verify_credential(self, credential):
        hasher = get_hasher(self.election.conf)
        return hasher.verify(credential, self.credential_hash)
    
    
    class Meta:
        abstract = True
        ordering = ['election', 'serial']
        unique_together = ['election', 'serial']
    
    class Manager(models.Manager):
        
        def get_by_natural_key(self, e_id, b_serial):
            
            manager = Election.objects.db_manager(self.db)
            election = manager.get_by_natural_key(e_id)
            
            return self.get(election=election, serial=b_serial)
    
    objects = Manager()
    
    def __str__(self):
        return "%s" % self.serial
    
    def natural_key(self):
        return self.election.natural_key() + (self.serial,)
    
    natural_key.dependencies = ['Election']


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
    
    # Custom methods and properties
    
    def verify_security_code(self, security_code):
        hasher = get_hasher(self.ballot.election.conf)
        return hasher.verify(security_code, self.security_code_hash)
    
    
    class Meta:
        abstract = True
        ordering = ['ballot', 'tag']
        unique_together = ['ballot', 'tag']
    
    class Manager(models.Manager):
        
        def get_by_natural_key(self, e_id, b_serial, p_tag):
            
            manager = Ballot.objects.db_manager(self.db)
            ballot = manager.get_by_natural_key(e_id, b_serial)
            
            return self.get(ballot=ballot, tag=p_tag)
    
    objects = Manager()
    
    def __str__(self):
        return "%s" % self.tag
    
    def natural_key(self):
        return self.ballot.natural_key() + (self.tag,)
    
    natural_key.dependencies = ['Ballot']


@python_2_unicode_compatible
class QuestionV(models.Model):
    
    part = models.ForeignKey('Part', related_name='questions', related_query_name='question')
    question_c = models.ForeignKey('QuestionC', related_name='questions_v', related_query_name='question_v')
    
    # Custom methods and properties
    
    def __getattr__(self, name):
        try:
            return getattr(self.question_c, name)
        except (AttributeError, RuntimeError):
            # RuntimeError: infinite recursion if question_c is not set
            raise AttributeError("'QuestionV' object has no attribute '%s'" % name)
    
    class Meta:
        abstract = True
        ordering = ['part', 'question_c']
        unique_together = ['part', 'question_c']
    
    class Manager(models.Manager):
        
        def get_by_natural_key(self, e_id, b_serial, p_tag, q_index):
            
            manager = Part.objects.db_manager(self.db)
            part = manager.get_by_natural_key(e_id, b_serial, p_tag)
            
            manager = QuestionC.objects.db_manager(self.db)
            question = manager.get_by_natural_key(e_id, q_index)
            
            return self.get(part=part, question_c=question_c)
    
    objects = Manager()
    
    def __str__(self):
        return "%s" % (self.index + 1)
    
    def natural_key(self):
        return self.part.natural_key() + self.question_c.natural_key()[1:]
    
    natural_key.dependencies = ['Part', 'QuestionC']


@python_2_unicode_compatible
class OptionV(models.Model):
    
    question = models.ForeignKey('QuestionV', related_name='options', related_query_name='option')
    index = models.PositiveSmallIntegerField()
    
    class Meta:
        abstract = True
        ordering = ['question', 'index']
        unique_together = ['question', 'index']
    
    class Manager(models.Manager):
        
        def get_by_natural_key(self, e_id, b_serial, p_tag, q_index, o_index):
            
            manager = QuestionV.objects.db_manager(self.db)
            question = manager.get_by_natural_key(e_id, b_serial, p_tag, q_index)
            
            return self.get(question=question, index=o_index)
    
    objects = Manager()
    
    def __str__(self):
        return "%s" % (self.index + 1)
    
    def natural_key(self):
        return self.question.natural_key() + (self.index,)
    
    natural_key.dependencies = ['QuestionV']


@python_2_unicode_compatible
class Trustee(models.Model):
    
    election = models.ForeignKey('Election', related_name='trustees', related_query_name='trustee')
    email = models.EmailField()
    
    class Meta:
        abstract = True
        unique_together = ['election', 'email']
    
    class Manager(models.Manager):
        
        def get_by_natural_key(self, e_id, t_email):
            
            manager = Election.objects.db_manager(self.db)
            election = manager.get_by_natural_key(e_id)
            
            return self.get(election=election, email=t_email)
    
    objects = Manager()
    
    def __str__(self):
        return "%s" % self.email
    
    def natural_key(self):
        return self.election.natural_key() + (self.email,)
    
    natural_key.dependencies = ['Election']


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
    rsa_pkey_bits = models.PositiveSmallIntegerField(default=constants.RSA_PKEY_BITS)
    
    ecc_curve = models.PositiveSmallIntegerField(default=constants.ECC_CURVE)
    
    hash_algorithm = models.CharField(max_length=32, default=constants.HASH_ALGORITHM)
    key_derivation = models.CharField(max_length=32, default=constants.KEY_DERIVATION)
    
    # Custom methods and properties
    
    @classmethod
    def defaults(cls):
        kwargs = {}
        for field in cls._meta.get_fields():
            if not (field.auto_created or field.is_relation):
                kwargs[field.name] = field.default
        return kwargs
    
    class Meta:
        abstract = True
        unique_together = ['version', 'receipt_len', 'votecode_len', 'security_code_len', 'credential_bits',
                           'rsa_pkey_bits', 'ecc_curve', 'hash_algorithm', 'key_derivation']
    
    class Manager(models.Manager):
        
        def get_by_natural_key(self, *args, **kwargs):
            
            fields = self.model._meta.unique_together[0]
            kwargs.update(dict(zip(fields, args)))
            
            return self.get(**kwargs)
    
    objects = Manager()
    
    def __str__(self):
        return "%s" % self.version
    
    def natural_key(self):
        return tuple([getattr(self, name) for name in self._meta.unique_together[0]])


@python_2_unicode_compatible
class Task(models.Model):
    
    task_id = models.UUIDField(unique=True)
    election = models.ForeignKey('Election', related_name='tasks', related_query_name='task')
    
    class Meta:
        abstract = True
    
    def __str__(self):
        return "%s | %s" % (self.election.id, self.task_id)

