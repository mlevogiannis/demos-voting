# File: api.py

from __future__ import absolute_import, division, print_function, unicode_literals

from demos_voting.apps.ea.models import APIAuthNonce
from demos_voting.common.utils.api import APIAuth, APISession, APIUser


class APIAuth(APIAuth):
    auth_nonce_cls = APIAuthNonce


class APISession(APISession):
    auth_cls = APIAuth


class APIUser(APIUser):
    user_permissions = {
        'bds': {'ea.change_election'},
        'abb': {'ea.change_election'},
        'vbb': {'ea.change_election'},
    }

