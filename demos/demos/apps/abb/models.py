# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

from django.conf import settings
from django.db import models

from demos.common.models import base
from demos.common.utils import crypto, fields, storage

logger = logging.getLogger(__name__)


fs_root = storage.PrivateFileSystemStorage(location=settings.DEMOS_DATA_DIR,
    file_permissions_mode=0o600, directory_permissions_mode=0o700)

def get_cert_file_path(election, filename):
    return "certs/%s%s" % (election.id, os.path.splitext(filename)[-1])


class Election(base.Election):
    
    cert = models.FileField(upload_to=get_cert_file_path, storage=fs_root)
    
    tallying_started_at = models.DateTimeField(null=True, default=None)
    tallying_ended_at = models.DateTimeField(null=True, default=None)
    
    coins = models.CharField(max_length=128, null=True, default=None)
    


class Ballot(base.Ballot):
    
    credential = models.CharField(max_length=32, null=True, default=None)
    credential_hash = models.CharField(max_length=128)
    
    cast_at = models.DateTimeField(null=True, default=None)


class Part(base.Part):
    
    security_code = models.CharField(max_length=32, null=True, default=None)
    security_code_hash = models.CharField(max_length=128)


class Question(base.Question):
    
    key = fields.ProtoField(cls=crypto.Key)
    
    com_combined = fields.ProtoField(cls=crypto.Com, null=True, default=None)
    decom_combined = fields.ProtoField(cls=crypto.Decom, null=True, default=None)


class Option_P(base.Option_P):
    
    votes = models.PositiveIntegerField(null=True, default=None)


class Option_C(base.Option_C):
    
    votecode = models.CharField(max_length=32, null=True, default=None)
    votecode_hash_value = models.CharField(max_length=128, null=True, default=None)
    
    voted = models.NullBooleanField(default=None)
    
    com = fields.ProtoField(cls=crypto.Com)
    zk1 = fields.ProtoField(cls=crypto.ZK1)
    zk2 = fields.ProtoField(cls=crypto.ZK2, null=True, default=None)
    
    receipt_full = models.CharField(max_length=1024)


class PartQuestion(base.PartQuestion):
    
    votecode_hash_salt = models.CharField(max_length=32, null=True, default=None)
    votecode_hash_params = models.CharField(max_length=16, null=True, default=None)


class Task(base.Task):
    pass


# Common models ----------------------------------------------------------------

from demos.common.utils.api import RemoteUserBase

class RemoteUser(RemoteUserBase):
    pass

