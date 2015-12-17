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
    pass


class Question(base.Question):
    
    columns = models.BooleanField(default=False)


class OptionC(base.OptionC):
    pass


class Ballot(base.Ballot):
    
    used = models.BooleanField(default=False)
    credential_hash = models.CharField(max_length=128)


class Part(base.Part):
    
    security_code_hash2 = models.CharField(max_length=128)
    
    l_votecode_salt = models.CharField(max_length=128, blank=True, default='')
    l_votecode_iterations = models.PositiveIntegerField(null=True, blank=True, default=None)


class OptionV(base.OptionV):
    
    votecode = models.PositiveSmallIntegerField()
    
    l_votecode_hash = models.CharField(max_length=128, blank=True, default='')
    
    receipt = models.CharField(max_length=conf.RECEIPT_LEN)


class Task(base.Task):
    pass


# Common models ----------------------------------------------------------------

from demos.common.utils.api import RemoteUserBase

class RemoteUser(RemoteUserBase):
    pass


