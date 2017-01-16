# File: api.py

from __future__ import absolute_import, division, print_function, unicode_literals

from demos_voting.apps.bds.models import APIAuthNonce
from demos_voting.common.utils.api import APIAuth, APISession, APIUser


class APIAuth(APIAuth):
    auth_nonce_cls = APIAuthNonce


class APISession(APISession):
    auth_cls = APIAuth


class APIUser(APIUser):
    user_permissions = {
        'ea': {'bds.add_election', 'bds.change_election', 'bds.add_ballot'},
    }

