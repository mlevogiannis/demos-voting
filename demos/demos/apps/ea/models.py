# File: models.py

from __future__ import division, unicode_literals

from django.db import models
from django.core import urlresolvers
from django.utils.encoding import python_2_unicode_compatible

from demos.common.utils import crypto, enums, fields, storage
from demos.common.utils.config import registry

config = registry.get_config('ea')


@python_2_unicode_compatible
class Election(models.Model):
    
    id = fields.Base32Field(primary_key=True)
    
    title = models.CharField(max_length=config.TITLE_MAXLEN)
    
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    
    state = fields.IntEnumField(cls=enums.State)
    vc_type = fields.IntEnumField(cls=enums.Vc)

    ballots = models.PositiveIntegerField()
    
    # Other model methods and meta options
    
    def __str__(self):
        return "%s - %s" % (self.id, self.title)
    
    def get_absolute_url(self):
        return urlresolvers.reverse('ea:manage', args=[self.id])
    
    class Meta:
        ordering = ['id']
    
    class ElectionManager(models.Manager):
        def get_by_natural_key(self, e_id):
            return self.get(id=e_id)
    
    objects = ElectionManager()
    
    def natural_key(self):
        return (self.id,)


@python_2_unicode_compatible
class Ballot(models.Model):
    
    election = models.ForeignKey(Election)
    
    serial = models.PositiveIntegerField()
    
    # Other model methods and meta options
    
    def __str__(self):
        return "%s" % self.serial
    
    class Meta:
        ordering = ['election', 'serial']
        unique_together = ['election', 'serial']
    
    class BallotManager(models.Manager):
        def get_by_natural_key(self, b_serial, e_id):
            return self.get(serial=b_serial, election__id=e_id)
    
    objects = BallotManager()
    
    def natural_key(self):
        return (self.serial,) + self.election.natural_key()


@python_2_unicode_compatible
class Part(models.Model):
    
    ballot = models.ForeignKey(Ballot)
    
    index = models.CharField(max_length=1, choices=(('A', 'A'), ('B', 'B')))
    
    # Other model methods and meta options
    
    def __str__(self):
        return "%s" % self.index
    
    class Meta:
        ordering = ['ballot', 'index']
        unique_together = ['ballot', 'index']
    
    class PartManager(models.Manager):
        def get_by_natural_key(self, p_index, b_serial, e_id):
            return self.get(index=p_index, ballot__serial=b_serial,
                ballot__election__id=e_id)
    
    objects = PartManager()
    
    def natural_key(self):
        return (self.index,) + self.ballot.natural_key()


@python_2_unicode_compatible
class Question(models.Model):
    
    election = models.ForeignKey(Election)
    m2m_parts = models.ManyToManyField(Part)
    
    text = models.CharField(max_length=config.QUESTION_MAXLEN)
    index = models.PositiveSmallIntegerField()
    
    # Other model methods and meta options
    
    def __str__(self):
        return "%s. %s" % (self.index + 1, self.text)
    
    class Meta:
        ordering = ['election', 'index']
        unique_together = ['election', 'index']
    
    class QuestionManager(models.Manager):
        def get_by_natural_key(self, q_index, e_id):
            return self.get(index=q_index, election__id=e_id)
    
    objects = QuestionManager()
    
    def natural_key(self):
        return (self.index,) + self.election.natural_key()


@python_2_unicode_compatible
class OptionV(models.Model):
    
    part = models.ForeignKey(Part)
    question = models.ForeignKey(Question)
    
    decom = fields.ProtoField(cls=crypto.Decom)
    zk_state = fields.ProtoField(cls=crypto.ZKState)
    
    index = models.PositiveSmallIntegerField()
    
    # Other model methods and meta options
    
    def __str__(self):
        return "%s" % (self.index + 1)
    
    class Meta:
        ordering = ['part', 'question', 'index']
        unique_together = ['part', 'question', 'index']
    
    class OptionVManager(models.Manager):
        def get_by_natural_key(self, o_index, q_index, p_index, b_serial, e_id):
            return self.get(index=o_index, part__ballot__serial=b_serial,
                question__index=q_index, question__election__id=e_id,
                part__index=p_index, part__ballot__election__id=e_id)
    
    objects = OptionVManager()
    
    def natural_key(self):
        return (self.index,) + \
            self.question.natural_key()[:-1] + self.part.natural_key()


@python_2_unicode_compatible
class OptionC(models.Model):
    
    question = models.ForeignKey(Question)
    
    text = models.CharField(max_length=config.OPTION_MAXLEN)
    index = models.PositiveSmallIntegerField()
    
    # Other model methods and meta options
    
    def __str__(self):
        return "%s. %s" % (self.index + 1, self.text)
    
    class Meta:
        ordering = ['question', 'index']
        unique_together = ['question', 'text']
    
    class OptionCManager(models.Manager):
        def get_by_natural_key(self, o_text, q_index, e_id):
            return self.get(text=o_text, question__index=q_index,
                question__election__id=e_id)
    
    objects = OptionCManager()
    
    def natural_key(self):
        return (self.text,) + self.question.natural_key()


@python_2_unicode_compatible
class Trustee(models.Model):
    
    election = models.ForeignKey(Election)
    
    email = models.EmailField()
    
    # Other model methods and meta options
    
    def __str__(self):
        return "%s" % self.email
    
    class Meta:
        unique_together = ['election', 'email']
    
    class TrusteeManager(models.Manager):
        def get_by_natural_key(self, t_email, e_id):
            return self.get(election__id=e_id, email=t_email)
    
    objects = TrusteeManager()
    
    def natural_key(self):
        return (self.email,) + self.election.natural_key()


class Task(models.Model):
    
    election = models.OneToOneField(Election, primary_key=True)
    task_id = models.UUIDField()


# Common models ----------------------------------------------------------------

from demos.common.utils.api import RemoteUserBase
from demos.common.utils.config import ConfigBase

class Config(ConfigBase):
    pass

class RemoteUser(RemoteUserBase):
    pass

