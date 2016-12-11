# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from demos_voting.common.models import (Election, Question, Option, Ballot, Part, PQuestion, POption, Task,
    PrivateApiUser, PrivateApiNonce)
from demos_voting.common.utils import base32

logger = logging.getLogger(__name__)


class Election(Election):

    ballot_distribution_started_at = models.DateTimeField(_("ballot distribution started at"), null=True, default=None)
    ballot_distribution_ended_at = models.DateTimeField(_("ballot distribution ended at"), null=True, default=None)


class Question(Question):
    pass


class Option(Option):
    pass


class Ballot(Ballot):

    credential = models.CharField(_("credential"), max_length=32)


class Part(Part):

    security_code = models.CharField(_("security code"), max_length=32, null=True)


class PQuestion(PQuestion):
    pass


class POption(POption):

    votecode = models.CharField(_("vote-code"), max_length=32)
    receipt = models.TextField(_("receipt"))


class Task(Task):
    pass


class PrivateApiUser(PrivateApiUser):
    pass


class PrivateApiNonce(PrivateApiNonce):
    pass
