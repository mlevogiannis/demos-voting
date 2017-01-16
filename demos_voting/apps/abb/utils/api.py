# File: api.py

from __future__ import absolute_import, division, print_function, unicode_literals

from demos_voting.apps.abb.models import APIAuthNonce
from demos_voting.common.utils.api import APIAuth, APISession, APIUser


class APIAuth(APIAuth):
    auth_nonce_cls = APIAuthNonce


class APISession(APISession):
    auth_cls = APIAuth


class APIUser(APIUser):
    user_permissions = {
        'ea': {'abb.add_election', 'abb.change_election', 'abb.add_ballot'},
        'vbb': {'abb.change_election'},
    }

