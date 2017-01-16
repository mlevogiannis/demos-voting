# File: api.py

from __future__ import absolute_import, division, print_function, unicode_literals

from demos_voting.apps.vbb.models import APIAuthNonce
from demos_voting.common.utils.api import APIAuth, APISession, APIUser


class APIAuth(APIAuth):
    auth_nonce_cls = APIAuthNonce


class APISession(APISession):
    auth_cls = APIAuth


class APIUser(APIUser):
    user_permissions = {
        'ea': {'vbb.add_election', 'vbb.change_election', 'vbb.add_ballot'},
    }

