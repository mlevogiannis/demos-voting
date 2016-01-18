# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

from django.apps import apps
from django.db import models

from demos.common.models import base
from demos.common.utils import storage

logger = logging.getLogger(__name__)

app_config = apps.get_app_config('bds')
conf = app_config.get_constants_and_settings()


ballot_fs = storage.PrivateTarFileStorage(
    location=os.path.join(conf.FILESYSTEM_ROOT, 'ballots'),
    tar_permissions_mode=0o600, tar_file_permissions_mode=0o600,
    tar_directory_permissions_mode=0o700
)

def get_ballot_file_path(ballot, filename):
    return "%s/%s" % (ballot.election.id, filename)


class Election(base.Election):
    
    ballot_distribution_started_at = models.DateTimeField(null=True, default=None)
    ballot_distribution_ended_at = models.DateTimeField(null=True, default=None)


class Ballot(base.Ballot):
    
    pdf = models.FileField(upload_to=get_ballot_file_path, storage=ballot_fs)


class Part(base.Part):
    
    voter_token = models.TextField()
    security_code = models.CharField(max_length=32)


class Conf(base.Conf):
    pass


class Task(base.Task):
    pass


# Common models ----------------------------------------------------------------

from demos.common.utils.api import RemoteUserBase

class RemoteUser(RemoteUserBase):
    pass

