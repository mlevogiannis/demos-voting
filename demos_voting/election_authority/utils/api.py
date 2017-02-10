# File: api.py

from __future__ import absolute_import, division, print_function, unicode_literals

from demos_voting.base.utils.api import APIAuth, APISession, APIUser
from demos_voting.election_authority.models import APIAuthNonce


class APIAuth(APIAuth):
    auth_nonce_cls = APIAuthNonce


class APISession(APISession):
    auth_cls = APIAuth


class APIUser(APIUser):
    user_permissions = {
        'ballot_distributor': {
            'election_authority.change_election'
        },
        'bulletin_board': {
            'election_authority.change_election'
        },
        'vote_collector': {
            'election_authority.change_election'
        },
    }

