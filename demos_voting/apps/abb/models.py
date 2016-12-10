# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from demos_voting.common import fields
from demos_voting.common.models import (Election, Question, Option, Ballot, Part, PQuestion, POption, Task,
    PrivateApiUser, PrivateApiNonce)

logger = logging.getLogger(__name__)


def certificate_directory_path(election, filename):
    return "abb/elections/%s/certificate.crt" % (election.id)


class Election(Election):

    certificate = models.FileField(_("certificate"), upload_to=certificate_directory_path)

    tallying_started_at = models.DateTimeField(_("tallying started at"), null=True, default=None)
    tallying_ended_at = models.DateTimeField(_("tallying ended at"), null=True, default=None)

    coins = models.TextField(_("voters' coins"), null=True, default=None)


class Question(Question):

    commitment_key = models.TextField(_("commitment key"))


class Option(Option):

    vote_count = models.PositiveIntegerField(_("number of votes"), null=True, default=None)


class Ballot(Ballot):

    credential = models.CharField(_("credential"), max_length=32, null=True, default=None)
    credential_hash = models.TextField(_("credential hash"))


class Part(Part):
    pass


class PQuestion(PQuestion):

    zk = fields.JSONField(_("zero-knowledge proof"))


class POption(POption):

    is_voted = models.NullBooleanField(_("marked as voted"), default=None)

    votecode = models.CharField(_("vote-code"), max_length=32, null=True, default=None)
    votecode_hash = models.TextField(_("vote-code hash"), null=True, default=None)

    receipt = models.TextField(_("receipt"))

    commitment = fields.JSONField(_("commitment"))
    zk1 = fields.JSONField(_("zero-knowledge proof ZK1"))


class Task(Task):
    pass


class PrivateApiUser(PrivateApiUser):
    pass


class PrivateApiNonce(PrivateApiNonce):
    pass

