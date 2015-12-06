# File: models.py

from __future__ import absolute_import, division, unicode_literals

import os
import logging

from django.db import models

from demos.common.models import base
from demos.common.utils import fields, storage
from demos.common.utils.config import registry

logger = logging.getLogger(__name__)
config = registry.get_config('bds')


class Election(base.Election):
    pass


ballot_fs = storage.PrivateTarFileStorage(
    location=os.path.join(config.FILESYSTEM_ROOT, 'ballots'),
    tar_permissions_mode=0o600, tar_file_permissions_mode=0o600,
    tar_directory_permissions_mode=0o700
)

def get_ballot_file_path(ballot, filename):
    return "%s/%s" % (ballot.election.id, filename)


class Ballot(base.Ballot):
    
    pdf = models.FileField(upload_to=get_ballot_file_path, storage=ballot_fs)


class Part(base.Part):
    
    vote_token = models.TextField()
    security_code = models.CharField(max_length=config.SECURITY_CODE_LEN)


class Task(base.Task):
    pass


# Common models ----------------------------------------------------------------

from demos.common.utils.api import RemoteUserBase
from demos.common.utils.config import ConfigBase

class Config(ConfigBase):
    pass

class RemoteUser(RemoteUserBase):
    pass

