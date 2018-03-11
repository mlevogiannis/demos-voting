from __future__ import absolute_import, division, print_function, unicode_literals

from demos_voting.base.utils.api import APISession


class BulletinBoardAPISession(APISession):
    client_username = 'ballot_distributor'
    server_username = 'bulletin_board'


class ElectionAuthorityAPISession(APISession):
    client_username = 'ballot_distributor'
    server_username = 'election_authority'


class VoteCollectorAPISession(APISession):
    client_username = 'ballot_distributor'
    server_username = 'vote_collector'
