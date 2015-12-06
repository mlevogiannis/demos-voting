# File: models.py

from __future__ import absolute_import, division, unicode_literals

import logging

from django.db import models

from demos.common.models import base
from demos.common.utils import fields
from demos.common.utils.config import registry

logger = logging.getLogger(__name__)
config = registry.get_config('vbb')


class Election(base.Election):
    pass


class Question(base.Question):
    
    choices = models.PositiveSmallIntegerField()
    columns = models.BooleanField(default=False)


class OptionC(base.OptionC):
    pass


class Ballot(base.Ballot):
    
    used = models.BooleanField(default=False)
    credential_hash = models.CharField(max_length=config.HASH_FIELD_LEN)


class Part(base.Part):
    
    security_code_hash2 = models.CharField(max_length=config.HASH_FIELD_LEN)
    
    # OptionV common data
    
    l_votecode_salt = models.CharField(max_length=config.HASH_FIELD_LEN,
        blank=True, default='')
    
    l_votecode_iterations = models.PositiveIntegerField(null=True,
        blank=True, default=None)


class OptionV(base.OptionV):
    
    votecode = models.PositiveSmallIntegerField()
    
    l_votecode_hash = models.CharField(max_length=config.HASH_FIELD_LEN,
        blank=True, default='')
    
    receipt = models.CharField(max_length=config.RECEIPT_LEN)


class Task(base.Task):
    pass


# Common models ----------------------------------------------------------------

from demos.common.utils.api import RemoteUserBase
from demos.common.utils.config import ConfigBase

class Config(ConfigBase):
    pass

class RemoteUser(RemoteUserBase):
    pass


