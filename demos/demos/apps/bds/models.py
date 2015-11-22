# File: models.py

from __future__ import division, unicode_literals

import os

from django.db import models
from django.core import urlresolvers
from django.utils.encoding import python_2_unicode_compatible

from demos.common.utils import enums, fields, storage
from demos.common.utils.config import registry

config = registry.get_config('bds')


@python_2_unicode_compatible
class Election(models.Model):
    
    id = fields.Base32Field(primary_key=True)
    
    title = models.CharField(max_length=config.TITLE_MAXLEN)
    
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    
    state = fields.IntEnumField(cls=enums.State)
    vc_type = fields.IntEnumField(cls=enums.VcType)
    
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


ballot_fs = storage.PrivateTarFileStorage(
    location=os.path.join(config.FILESYSTEM_ROOT, 'ballots'),
    tar_permissions_mode=0o600, tar_file_permissions_mode=0o600,
    tar_directory_permissions_mode=0o700
)

def get_ballot_file_path(ballot, filename):
    return "%s/%s" % (ballot.election.id, filename)


@python_2_unicode_compatible
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


@python_2_unicode_compatible
class Part(models.Model):
    
    ballot = models.ForeignKey(Ballot)
    
    index = models.CharField(max_length=1, choices=(('A', 'A'), ('B', 'B')))
    
    vote_token = models.TextField()
    security_code = models.CharField(max_length=config.SECURITY_CODE_LEN)
    
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

