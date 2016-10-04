# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import re

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from demos_voting.common.models import (Election, Ballot, Part, Question, Option_P, Option_C, PartQuestion, Task,
    PrivateApiUser, PrivateApiNonce)
from demos_voting.common.utils import base32
from demos_voting.common.utils.hashers import get_hasher, identify_hasher

logger = logging.getLogger(__name__)


class Election(Election):
    
    voting_started_at = models.DateTimeField(_("voting started at"), null=True, default=None)
    voting_ended_at = models.DateTimeField(_("voting ended at"), null=True, default=None)


class Ballot(Ballot):
    
    cast_at = models.DateTimeField(_("cast at"), null=True, default=None)
    
    @property
    def is_cast(self):
        return self.cast_at is not None


class Part(Part):
    
    credential_hash = models.CharField(_("credential hash"), max_length=255)
    
    def verify_credential(self, credential):
        hasher = get_hasher(identify_hasher(self.credential_hash))
        regex = r'^%s{%d}$' % (base32.regex, (self.election.credential_length * 8 + 4) // 5)
        return (re.match(regex, credential) and hasher.verify(base32.normalize(credential), self.credential_hash))


class Question(Question):
    pass


class Option_P(Option_P):
    pass


class Option_C(Option_C):
    
    votecode = models.CharField(_("vote-code"), max_length=32, null=True, default=None)
    votecode_hash = models.CharField(_("vote-code hash"), max_length=255, null=True, default=None)
    
    receipt = models.CharField(_("receipt"), max_length=1024)


class PartQuestion(PartQuestion):
    pass


class Task(Task):
    pass


class PrivateApiUser(PrivateApiUser):
    pass


class PrivateApiNonce(PrivateApiNonce):
    pass

