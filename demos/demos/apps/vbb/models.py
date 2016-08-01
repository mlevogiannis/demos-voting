# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import re

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from demos.common.models import (
    Election, Ballot, Part, Question, Option_P, Option_C, PartQuestion, Task,
    PrivateApiUser
)
from demos.common.utils import base32

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
    
    credential_hash = models.CharField(_("credential hash value"), max_length=128)
    
    def verify_credential(self, credential):
        hasher = self.election.hasher
        regex = r'^%s{%d}$' % (base32.regex, (self.election.credential_bits + 4) // 5)
        return (re.match(regex, credential) and hasher.verify(base32.normalize(credential), self.credential_hash))


class Question(Question):
    pass


class Option_P(Option_P):
    pass


class Option_C(Option_C):
    
    votecode = models.CharField(_("vote-code"), max_length=32, null=True, default=None)
    votecode_hash_value = models.CharField(_("vote-code hash value"), max_length=128, null=True, default=None)
    
    receipt = models.CharField(_("receipt"), max_length=1024)


class PartQuestion(PartQuestion):
    
    votecode_hash_salt = models.CharField(max_length=32, null=True, default=None)
    votecode_hash_params = models.CharField(max_length=16, null=True, default=None)


class Task(Task):
    pass


class PrivateApiUser(PrivateApiUser):
    pass

