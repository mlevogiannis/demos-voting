# File: api.py

from __future__ import absolute_import, division, print_function, unicode_literals

from demos_voting.base.utils.api import APIAuth, APISession, APIUser
from demos_voting.bulletin_board.models import APIAuthNonce


class APIAuth(APIAuth):
    auth_nonce_cls = APIAuthNonce


class APISession(APISession):
    auth_cls = APIAuth


class APIUser(APIUser):
    user_permissions = {
        'election_authority': {
            'bulletin_board.add_election',
            'bulletin_board.change_election',
            'bulletin_board.add_ballot'
        },
        'vote_collector': {
            'bulletin_board.change_election'
        },
    }

