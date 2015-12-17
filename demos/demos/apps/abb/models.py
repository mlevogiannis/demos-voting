# File: models.py

from __future__ import absolute_import, division, unicode_literals

import logging
import os

from django.apps import apps
from django.db import models

from demos.common.models import base
from demos.common.utils import crypto, fields, storage

logger = logging.getLogger(__name__)

app_config = apps.get_app_config('abb')
conf = app_config.get_constants_and_settings()


fs_root = storage.PrivateFileSystemStorage(location=conf.FILESYSTEM_ROOT,
    file_permissions_mode=0o600, directory_permissions_mode=0o700)

def get_cert_file_path(election, filename):
    return "certs/%s%s" % (election.id, os.path.splitext(filename)[-1])

def get_export_file_path(election, filename):
    return "export/%s%s" % (election.id, os.path.splitext(filename)[-1])


class Election(base.Election):
    
    cert = models.FileField(upload_to=get_cert_file_path, storage=fs_root)
    export_file = models.FileField(upload_to=get_export_file_path, storage=fs_root, blank=True)
    
    # Post-voting data
    
    coins = models.CharField(max_length=128, blank=True, default='')


class Question(base.Question):
    
    key = fields.ProtoField(cls=crypto.Key)
    
    # Post-voting data
    
    combined_com = fields.ProtoField(cls=crypto.Com, null=True, blank=True, default=None)
    combined_decom = fields.ProtoField(cls=crypto.Decom, null=True, blank=True, default=None)


class OptionC(base.OptionC):
    
    # Post-voting data
    
    votes = models.PositiveIntegerField(null=True, blank=True, default=None)


class Ballot(base.Ballot):
    
    credential_hash = models.CharField(max_length=128)


class Part(base.Part):
    
    security_code = models.CharField(max_length=conf.SECURITY_CODE_LEN, blank=True, default='')
    security_code_hash2 = models.CharField(max_length=128)
    
    l_votecode_salt = models.CharField(max_length=128, blank=True, default='')
    l_votecode_iterations = models.PositiveIntegerField(null=True, blank=True, default=None)


class OptionV(base.OptionV):
    
    votecode = models.PositiveSmallIntegerField()
    
    l_votecode = models.CharField(max_length=conf.VOTECODE_LEN, blank=True, default='')
    l_votecode_hash = models.CharField(max_length=128, blank=True, default='')
    
    com = fields.ProtoField(cls=crypto.Com)
    zk1 = fields.ProtoField(cls=crypto.ZK1)
    zk2 = fields.ProtoField(cls=crypto.ZK2, null=True, blank=True, default=None)
    
    receipt_full = models.TextField()
    
    voted = models.NullBooleanField(default=None)


class Conf(base.Conf):
    pass


class Task(base.Task):
    pass


# Common models ----------------------------------------------------------------

from demos.common.utils.api import RemoteUserBase

class RemoteUser(RemoteUserBase):
    pass

