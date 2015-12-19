# File: models.py

from __future__ import absolute_import, division, unicode_literals

import logging

from django.apps import apps
from django.db import models

from demos.common.models import base

logger = logging.getLogger(__name__)

app_config = apps.get_app_config('vbb')
conf = app_config.get_constants_and_settings()


class Election(base.Election):
    
    voting_started_at = models.DateTimeField(null=True, default=None)
    voting_finished_at = models.DateTimeField(null=True, default=None)


class Question(base.Question):
    
    columns = models.BooleanField(default=False)


class OptionC(base.OptionC):
    pass


class Ballot(base.Ballot):
    
    credential_hash = models.CharField(max_length=128)
    cast_at = models.DateTimeField(null=True, default=None)


class Part(base.Part):
    
    security_code_hash = models.CharField(max_length=128)
    
    votecode_hash_salt = models.CharField(max_length=24, null=True, default=None)
    votecode_hash_params = models.CharField(max_length=16, null=True, default=None)


class OptionV(base.OptionV):
    
    votecode = models.CharField(max_length=32, null=True, default=None)
    votecode_hash = models.CharField(max_length=128, null=True, default=None, db_column='votecode_hash')
    
    receipt = models.CharField(max_length=32)


class Conf(base.Conf):
    pass


class Task(base.Task):
    pass


# Common models ----------------------------------------------------------------

from demos.common.utils.api import RemoteUserBase

class RemoteUser(RemoteUserBase):
    pass


