from __future__ import absolute_import, division, print_function, unicode_literals

import rules


# REST API roles ##############################################################

# The usernames `ballot_distributor`, `bulletin_board`, `election_authority`
# and `vote_collector` are reserved to be used only by the system's users.

@rules.predicate
def is_ballot_distributor(user):
    return user.is_authenticated and user.username == 'ballot_distributor'


@rules.predicate
def is_bulletin_board(user):
    return user.is_authenticated and user.username == 'bulletin_board'


@rules.predicate
def is_election_authority(user):
    return user.is_authenticated and user.username == 'election_authority'


@rules.predicate
def is_vote_collector(user):
    return user.is_authenticated and user.username == 'vote_collector'


rules.add_perm('base.is_ballot_distributor', is_ballot_distributor)
rules.add_perm('base.is_bulletin_board', is_bulletin_board)
rules.add_perm('base.is_election_authority', is_election_authority)
rules.add_perm('base.is_vote_collector', is_vote_collector)
