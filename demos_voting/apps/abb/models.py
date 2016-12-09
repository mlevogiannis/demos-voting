# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from demos_voting.common.models import (Election, Question, Option, Ballot, Part, PQuestion, POption, Task,
    PrivateApiUser, PrivateApiNonce)

logger = logging.getLogger(__name__)


def certificate_directory_path(election, filename):
    return "abb/elections/%s/certificate.crt" % (election.id)


class Election(Election):

    certificate = models.FileField(_("certificate"), upload_to=certificate_directory_path)

    tallying_started_at = models.DateTimeField(_("tallying started at"), null=True, default=None)
    tallying_ended_at = models.DateTimeField(_("tallying ended at"), null=True, default=None)

    coins = models.CharField(_("coins"), max_length=128, null=True, default=None)


class Question(Question):
    pass


class Option(Option):

    votes = models.PositiveIntegerField(_("number of votes"), null=True, default=None)


class Ballot(Ballot):

    cast_at = models.DateTimeField(_("cast at"), null=True, default=None)

    credential = models.CharField(_("credential"), max_length=32, null=True, default=None)
    credential_hash = models.CharField(_("credential hash"), max_length=255)


class Part(Part):
    pass


class PQuestion(PQuestion):
    pass


class POption(POption):

    voted = models.NullBooleanField(_("marked as voted"), default=None)

    votecode = models.CharField(_("vote-code"), max_length=32, null=True, default=None)
    votecode_hash = models.CharField(_("vote-code hash"), max_length=255, null=True, default=None)

    receipt = models.CharField(_("receipt"), max_length=1024)


class Task(Task):
    pass


class PrivateApiUser(PrivateApiUser):
    pass


class PrivateApiNonce(PrivateApiNonce):
    pass

