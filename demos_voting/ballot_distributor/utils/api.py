# File: api.py

from __future__ import absolute_import, division, print_function, unicode_literals

from demos_voting.ballot_distributor.models import APIAuthNonce
from demos_voting.base.utils.api import APIAuth, APISession, APIUser


class APIAuth(APIAuth):
    auth_nonce_cls = APIAuthNonce


class APISession(APISession):
    auth_cls = APIAuth


class APIUser(APIUser):
    user_permissions = {
        'election_authority': {
            'ballot_distributor.add_election',
            'ballot_distributor.change_election',
            'ballot_distributor.add_ballot'
        },
    }

