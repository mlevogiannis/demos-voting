from __future__ import absolute_import, division, print_function, unicode_literals

from demos_voting.base.utils.api import APISession


class BallotDistributorAPISession(APISession):
    client_username = 'vote_collector'
    server_username = 'ballot_distributor'


class BulletinBoardAPISession(APISession):
    client_username = 'vote_collector'
    server_username = 'bulletin_board'


class ElectionAuthorityAPISession(APISession):
    client_username = 'vote_collector'
    server_username = 'election_authority'
