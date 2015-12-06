# File: models.py

from __future__ import absolute_import, division, unicode_literals

import os
import logging

from django.db import models

from demos.common.models import base
from demos.common.utils import crypto, fields, storage
from demos.common.utils.config import registry

logger = logging.getLogger(__name__)
config = registry.get_config('abb')


fs_root = storage.PrivateFileSystemStorage(location=config.FILESYSTEM_ROOT,
    file_permissions_mode=0o600, directory_permissions_mode=0o700)

def get_cert_file_path(election, filename):
    return "certs/%s%s" % (election.id, os.path.splitext(filename)[-1])

def get_export_file_path(election, filename):
    return "export/%s%s" % (election.id, os.path.splitext(filename)[-1])


class Election(base.Election):
    
    cert = models.FileField(upload_to=get_cert_file_path, storage=fs_root)
    export_file = models.FileField(upload_to=get_export_file_path,
        storage=fs_root, blank=True)
    
    # Post-voting data
    
    coins = models.CharField(max_length=config.HASH_FIELD_LEN, blank=True,
        default='')


class Question(base.Question):
    
    key = fields.ProtoField(cls=crypto.Key)
    choices = models.PositiveSmallIntegerField()
    
    # Post-voting data
    
    combined_com = fields.ProtoField(cls=crypto.Com, null=True, blank=True,
        default=None)
    
    combined_decom = fields.ProtoField(cls=crypto.Decom, null=True, blank=True,
        default=None)


class OptionC(base.OptionC):
    
    # Post-voting data
    
    votes = models.PositiveIntegerField(null=True, blank=True, default=None)


class Ballot(base.Ballot):
    
    credential_hash = models.CharField(max_length=config.HASH_FIELD_LEN)


class Part(base.Part):
    
    security_code = models.CharField(max_length=config.SECURITY_CODE_LEN,
        blank=True, default='')
    
    security_code_hash2 = models.CharField(max_length=config.HASH_FIELD_LEN)
    
    # OptionV common data
    
    l_votecode_salt = models.CharField(max_length=config.HASH_FIELD_LEN,
        blank=True, default='')
    
    l_votecode_iterations = models.PositiveIntegerField(null=True,
        blank=True, default=None)


class OptionV(base.OptionV):
    
    votecode = models.PositiveSmallIntegerField()
    
    l_votecode = models.CharField(max_length=config.VOTECODE_LEN,
        blank=True, default='')
    
    l_votecode_hash = models.CharField(max_length=config.HASH_FIELD_LEN,
        blank=True, default='')
    
    com = fields.ProtoField(cls=crypto.Com)
    zk1 = fields.ProtoField(cls=crypto.ZK1)
    zk2 = fields.ProtoField(cls=crypto.ZK2, null=True, blank=True, default=None)
    
    receipt_full = models.TextField()
    
    voted = models.NullBooleanField(default=None)


class Task(base.Task):
    pass


# Common models ----------------------------------------------------------------

from demos.common.utils.api import RemoteUserBase
from demos.common.utils.config import ConfigBase

class Config(ConfigBase):
    pass

class RemoteUser(RemoteUserBase):
    pass

