# File: models.py

from django.db import models
from django.core import urlresolvers

from demos.common.utils import config, enums, fields, storage


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
    
    # Other model methods and meta options
    
    def __str__(self):
        return "%s - %s" % (self.id, self.title)
    
    def get_absolute_url(self):
        return urlresolvers.reverse('bds:', args=[self.id])
    
    class Meta:
        ordering = ['id']
    
    class ElectionManager(models.Manager):
        def get_by_natural_key(self, e_id):
            return self.get(id=e_id)
    
    objects = ElectionManager()
    
    def natural_key(self):
        return (self.id,)


ballot_fs = storage.PrivateTarFileStorage(location=config.BALLOT_ROOT,
    tar_permissions_mode=0o600, tar_file_permissions_mode=0o600,
    tar_directory_permissions_mode=0o700)

def get_ballot_file_path(ballot, filename):
    return "%s/%s" % (ballot.election.id, filename)


class Ballot(models.Model):
    
    election = models.ForeignKey(Election)
    
    serial = models.PositiveIntegerField()
    pdf = models.FileField(upload_to=get_ballot_file_path, storage=ballot_fs)
    
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
    
    vote_token = models.TextField()
    security_code = models.CharField(max_length=config.SECURITY_CODE_LEN)
    
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

