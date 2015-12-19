# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from django.apps import apps
from django.db import models

from demos.common.models import base
from demos.common.utils import crypto, fields

logger = logging.getLogger(__name__)

app_config = apps.get_app_config('ea')
conf = app_config.get_constants_and_settings()


class Election(base.Election):
    
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    setup_started_at = models.DateTimeField(null=True, default=None)
    setup_finished_at = models.DateTimeField(null=True, default=None)


class Question(base.Question):
    pass


class OptionC(base.OptionC):
    pass


class Ballot(base.Ballot):
    pass


class Part(base.Part):
    pass


class OptionV(base.OptionV):
    
    decom = fields.ProtoField(cls=crypto.Decom)
    zk_state = fields.ProtoField(cls=crypto.ZKState)


class Trustee(base.Trustee):
    pass


class Conf(base.Conf):
    pass


class Task(base.Task):
    pass


# Common models ----------------------------------------------------------------

from demos.common.utils.api import RemoteUserBase

class RemoteUser(RemoteUserBase):
    pass

