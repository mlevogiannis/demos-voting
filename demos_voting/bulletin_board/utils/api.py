from __future__ import absolute_import, division, print_function, unicode_literals

from demos_voting.base.utils.api import APISession


class BallotDistributorAPISession(APISession):
    client_username = 'bulletin_board'
    server_username = 'ballot_distributor'


class ElectionAuthorityAPISession(APISession):
    client_username = 'bulletin_board'
    server_username = 'election_authority'


class VoteCollectorAPISession(APISession):
    client_username = 'bulletin_board'
    server_username = 'vote_collector'
