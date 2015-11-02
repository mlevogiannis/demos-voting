# File: models.py

from django.db import models
from django.core import urlresolvers

from demos.common.utils import enums, fields
from demos.common.utils.config import registry

config = registry.get_config('vbb')


class Config(models.Model):
    
    key = models.CharField(max_length=128, unique=True)
    value = models.CharField(max_length=128)
    
    # Other model methods and meta options
    
    def __str__(self):
        return "%s - %s" % (self.key, self.value)
    
    class ConfigManager(models.Manager):
        def get_by_natural_key(self, key):
            return self.get(key=key)
    
    objects = ConfigManager()
    
    def natural_key(self):
        return (self.key,)


class Election(models.Model):
    
    id = fields.Base32Field(primary_key=True)
    
    title = models.CharField(max_length=config.TITLE_MAXLEN)
    
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    
    long_votecodes = models.BooleanField()
    state = fields.IntEnumField(cls=enums.State)
    
    ballots = models.PositiveIntegerField()
    
    # Other model methods and meta options
    
    def __str__(self):
        return "%s - %s" % (self.id, self.title)
    
    def get_absolute_url(self):
        return urlresolvers.reverse('vbb:', args=[self.id])
    
    class Meta:
        ordering = ['id']
    
    class ElectionManager(models.Manager):
        def get_by_natural_key(self, e_id):
            return self.get(id=e_id)
    
    objects = ElectionManager()
    
    def natural_key(self):
        return (self.id,)


class Ballot(models.Model):
    
    election = models.ForeignKey(Election)
    
    serial = models.PositiveIntegerField()
    credential_hash = models.CharField(max_length=config.HASH_LEN)
    
    used = models.BooleanField(default=False)
    
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


class Part(models.Model):
    
    ballot = models.ForeignKey(Ballot)
    
    tag = models.CharField(max_length=1, choices=(('A', 'A'), ('B', 'B')))
    security_code_hash2 = models.CharField(max_length=config.HASH_LEN)
    
    # OptionV common data
    
    l_votecode_salt = models.CharField(max_length=config.HASH_LEN,
        blank=True, default='')
    
    l_votecode_iterations = models.PositiveIntegerField(null=True,
        blank=True, default=None)
    
    # Other model methods and meta options
    
    def __str__(self):
        return "%s" % self.tag
    
    class Meta:
        ordering = ['ballot', 'tag']
        unique_together = ['ballot', 'tag']
    
    class PartManager(models.Manager):
        def get_by_natural_key(self, p_tag, b_serial, e_id):
            return self.get(tag=p_tag, ballot__serial=b_serial,
                ballot__election__id=e_id)
    
    objects = PartManager()
    
    def natural_key(self):
        return (self.tag,) + self.ballot.natural_key()


class Question(models.Model):
    
    election = models.ForeignKey(Election)
    m2m_parts = models.ManyToManyField(Part)
    
    text = models.CharField(max_length=config.QUESTION_MAXLEN)
    choices = models.PositiveSmallIntegerField()
    
    index = models.PositiveSmallIntegerField()
    columns = models.BooleanField(default=False)
    
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


class OptionV(models.Model):
    
    part = models.ForeignKey(Part)
    question = models.ForeignKey(Question)
    
    votecode = models.PositiveSmallIntegerField()
    
    l_votecode_hash = models.CharField(max_length=config.HASH_LEN,
        blank=True, default='')
    
    receipt = models.CharField(max_length=config.RECEIPT_LEN)
    index = models.PositiveSmallIntegerField()
    
    # Other model methods and meta options
    
    def __str__(self):
        return "%s - %s" % (self.index + 1, self.votecode)
    
    class Meta:
        ordering = ['part', 'question', 'index']
        unique_together = ['part', 'question', 'index']
    
    class OptionVManager(models.Manager):
        def get_by_natural_key(self, o_index, q_index, p_tag, b_serial, e_id):
            return self.get(index=o_index, part__ballot__serial=b_serial,
                question__index=q_index, question__election__id=e_id,
                part__tag=p_tag, part__ballot__election__id=e_id)
    
    objects = OptionVManager()
    
    def natural_key(self):
        return (self.index,) + \
            self.question.natural_key()[:-1] + self.part.natural_key()


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


class RemoteUser(models.Model):
    
    username = models.CharField(max_length=128, unique=True)
    password = models.CharField(max_length=128)
    
    # Other model methods and meta options
    
    def __str__(self):
        return "%s - %s" % (self.username, self.password)
    
    class RemoteUserManager(models.Manager):
        def get_by_natural_key(self, username):
            return self.get(username=username)
    
    objects = RemoteUserManager()
    
    def natural_key(self):
        return (self.username,)


class Task(models.Model):
    
    task_id = models.UUIDField()
    election_id = fields.Base32Field(unique=True)

