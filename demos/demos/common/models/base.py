# File: base.py

from __future__ import absolute_import, division, unicode_literals

import logging

from django.core import validators
from django.db import models
from django.db.models import Count, Max, Min
from django.utils.encoding import python_2_unicode_compatible

from demos.common.conf import constants
from demos.common.utils import base32cf, enums, fields

logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class Election(models.Model):
    
    id = models.CharField(db_column='e_id', unique=True, max_length=16,
        validators=[validators.RegexValidator(regex=base32cf.re_valid)])
    
    state = fields.IntEnumField(cls=enums.State)

    type = fields.IntEnumField(cls=enums.Type)
    vc_type = fields.IntEnumField(cls=enums.VcType)
    
    name = models.CharField(max_length=constants.ELECTION_MAXLEN)
    
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()

    
    
    # Custom methods and properties
    
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
    
    def save(self, *args, **kwargs):
        self.id = base32cf.normalize(self.id)
        super(Election, self).save(*args, **kwargs)


@python_2_unicode_compatible
class Question(models.Model):
    
    election = models.ForeignKey('Election', related_name='questions', related_query_name='question')
    parts = models.ManyToManyField('Part', related_name='questions', related_query_name='question')
    
    index = models.PositiveSmallIntegerField()
    text = models.CharField(max_length=constants.QUESTION_MAXLEN)
    
    # Custom methods and properties
    
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
    text = models.CharField(max_length=constants.OPTION_MAXLEN)
    
    # Predefined methods and meta options
    
    class Meta:
        abstract = True
        ordering = ['question', 'index']
        unique_together = ['question', 'text']
        verbose_name = 'option_c'
    
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
    
    ballot = models.ForeignKey('Ballot', related_name='parts', related_query_name='part')
    tag = models.CharField(max_length=1, choices=(('A', 'A'), ('B', 'B')))
    
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
        verbose_name = 'option_v'
    
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


class Task(models.Model):
    
    task_id = models.UUIDField(unique=True)
    election = models.ForeignKey('Election', related_name='tasks', related_query_name='task')
    
    # Predefined methods and meta options
    
    class Meta:
        abstract = True
    
    def __str__(self):
        return "%s | %s" % (self.election.id, self.task_id)

