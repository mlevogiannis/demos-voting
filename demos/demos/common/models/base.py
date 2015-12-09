# File: base.py

from __future__ import absolute_import, division, unicode_literals

import logging

from django.core import validators
from django.db import models
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

    ballot_cnt = models.PositiveIntegerField()
    
    
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


@python_2_unicode_compatible
class Question(models.Model):
    
    election = models.ForeignKey('Election')
    part_set = models.ManyToManyField('Part')
    
    index = models.PositiveSmallIntegerField()
    text = models.CharField(max_length=constants.QUESTION_MAXLEN)

    option_cnt = models.PositiveSmallIntegerField()
    
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
    
    question = models.ForeignKey('Question')
    
    index = models.PositiveSmallIntegerField()
    text = models.CharField(max_length=constants.OPTION_MAXLEN)
    
    # Predefined methods and meta options
    
    class Meta:
        abstract = True
        ordering = ['question', 'index']
        unique_together = ['question', 'text']
    
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
    
    election = models.ForeignKey('Election')
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
    
    ballot = models.ForeignKey('Ballot')
    index = models.CharField(max_length=1, choices=(('A', 'A'), ('B', 'B')))
    
    # Predefined methods and meta options
    
    class Meta:
        abstract = True
        ordering = ['ballot', 'index']
        unique_together = ['ballot', 'index']
    
    class PartManager(models.Manager):
        
        def get_by_natural_key(self, e_id, b_serial, p_index):
            
            manager = Ballot.objects.db_manager(self.db)
            ballot = manager.get_by_natural_key(e_id, b_serial)
            
            return self.get(ballot=ballot, index=p_index)
    
    objects = PartManager()
    
    def __str__(self):
        return "%s" % self.index
    
    def natural_key(self):
        return self.ballot.natural_key() + (self.index,)
    
    natural_key.dependencies = ['%(app_label)s.Ballot']


@python_2_unicode_compatible
class OptionV(models.Model):
    
    part = models.ForeignKey('Part')
    question = models.ForeignKey('Question')
    
    index = models.PositiveSmallIntegerField()
    
    # Predefined methods and meta options
    
    class Meta:
        abstract = True
        ordering = ['part', 'question', 'index']
        unique_together = ['part', 'question', 'index']
    
    class OptionVManager(models.Manager):
        
        def get_by_natural_key(self, e_id, b_serial, p_index, q_index, o_index):
            
            manager = Part.objects.db_manager(self.db)
            part = manager.get_by_natural_key(e_id, b_serial, p_index)
            
            manager = Question.objects.db_manager(self.db)
            question = manager.get_by_natural_key(e_id, q_index)
            
            return self.get(part=part, question=question, index=o_index)
    
    objects = OptionVManager()
    
    def __str__(self):
        return "%s" % (self.index + 1)
    
    def natural_key(self):
        return self.part.natural_key() + \
            self.question.natural_key()[1:] + (self.index,)
    
    natural_key.dependencies = ['%(app_label)s.Part', '%(app_label)s.Question']


@python_2_unicode_compatible
class Trustee(models.Model):
    
    election = models.ForeignKey('Election')
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
    election = models.ForeignKey('Election')
    
    # Predefined methods and meta options
    
    class Meta:
        abstract = True
    
    def __str__(self):
        return "%s | %s" % (self.election.id, self.task_id)

