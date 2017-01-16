# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import re

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from demos_voting.common.models import Election, Question, Option, Ballot, Part, PQuestion, POption, Task, APIAuthNonce
from demos_voting.common.utils import base32
from demos_voting.common.utils.hashers import get_hasher, identify_hasher

logger = logging.getLogger(__name__)


class Election(Election):

    voting_started_at = models.DateTimeField(_("voting started at"), null=True, default=None)
    voting_ended_at = models.DateTimeField(_("voting ended at"), null=True, default=None)


class Question(Question):
    pass


class Option(Option):
    pass


class Ballot(Ballot):

    cast_at = models.DateTimeField(_("cast at"), null=True, default=None)

    credential_hash = models.TextField(_("credential hash"))

    @property
    def is_cast(self):
        return self.cast_at is not None

    def verify_credential(self, credential):
        hasher = get_hasher(identify_hasher(self.credential_hash))
        regex = r'^%s{%d}$' % (base32.regex, (self.election.credential_length * 8 + 4) // 5)
        return (re.match(regex, credential) and hasher.verify(base32.normalize(credential), self.credential_hash))


class Part(Part):
    pass


class PQuestion(PQuestion):
    pass


class POption(POption):

    votecode = models.CharField(_("vote-code"), max_length=32, null=True, default=None)
    votecode_hash = models.TextField(_("vote-code hash"), null=True, default=None)

    receipt = models.TextField(_("receipt"))


class Task(Task):
    pass


class APIAuthNonce(APIAuthNonce):
    pass

