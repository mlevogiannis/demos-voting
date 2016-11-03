# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

from django.conf import settings
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from demos_voting.common.models import (Election, Ballot, Part, Question, Option_P, Option_C, PartQuestion, Task,
    PrivateApiUser, PrivateApiNonce)
from demos_voting.common.utils import base32

logger = logging.getLogger(__name__)


class Election(Election):

    ballot_distribution_started_at = models.DateTimeField(_("ballot distribution started at"), null=True, default=None)
    ballot_distribution_ended_at = models.DateTimeField(_("ballot distribution ended at"), null=True, default=None)


class Ballot(Ballot):
    pass


class Part(Part):

    credential = models.CharField(_("credential"), max_length=32)
    security_code = models.CharField(_("security code"), max_length=32, null=True)

    @cached_property
    def token(self):

        serial_number_bits = (100 + self.election.ballots.count() - 1).bit_length()
        tag_bits = 1
        credential_bits = self.election.credential_length * 8

        serial_number = self.ballot.serial_number
        tag = (Part.TAG_A, Part.TAG_B).index(self.tag)
        credential = base32.decode(self.credential)

        t = (credential | (tag << credential_bits) | (serial_number << (tag_bits + credential_bits)))

        token_bits = serial_number_bits + tag_bits + credential_bits
        token_length = (token_bits + 4) // 5

        padding_bits = (token_length * 5) - token_bits

        if padding_bits > 0:
            t |= (random.getrandbits(padding_bits) << token_bits)

        return base32.encode(t, token_length)


class Question(Question):
    pass


class Option_P(Option_P):
    pass


class Option_C(Option_C):

    votecode = models.CharField(_("vote-code"), max_length=32)
    receipt = models.CharField(_("receipt"), max_length=1024)


class PartQuestion(PartQuestion):
    pass


class Task(Task):
    pass


class PrivateApiUser(PrivateApiUser):
    pass


class PrivateApiNonce(PrivateApiNonce):
    pass

