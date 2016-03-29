# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from demos.common.models import base
from demos.common.utils import storage

logger = logging.getLogger(__name__)


ballot_fs = storage.PrivateTarFileStorage(
    location=os.path.join(settings.DEMOS_DATA_DIR, 'bds/ballots'),
    tar_permissions_mode=0o600, tar_file_permissions_mode=0o600,
    tar_directory_permissions_mode=0o700
)

def get_ballot_file_path(ballot, filename):
    return "%s/%s" % (ballot.election.id, filename)


class Election(base.Election):
    
    ballot_distribution_started_at = models.DateTimeField(_("ballot distribution started at"), null=True, default=None)
    ballot_distribution_ended_at = models.DateTimeField(_("ballot distribution ended at"), null=True, default=None)


class Ballot(base.Ballot):
    
    pdf = models.FileField(_("PDF file"), upload_to=get_ballot_file_path, storage=ballot_fs)


class Part(base.Part):
    
    token = models.CharField(_("token"), max_length=64)
    security_code = models.CharField(_("security code"), max_length=32)


class Task(base.Task):
    pass


# Common models ----------------------------------------------------------------

from demos.common.utils.api import RemoteUserBase

class RemoteUser(RemoteUserBase):
    pass

