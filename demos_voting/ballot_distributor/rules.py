from __future__ import absolute_import, division, print_function, unicode_literals

import rules


@rules.predicate
def is_election_administrator(user, election):
    return user.is_authenticated and election.administrators.filter(user=user).exists()


rules.add_perm('ballot_distributor.can_view_election', is_election_administrator)
rules.add_perm('ballot_distributor.can_edit_election', is_election_administrator)
rules.add_perm('ballot_distributor.can_create_ballot_archive', is_election_administrator)
rules.add_perm('ballot_distributor.can_create_voter_list', is_election_administrator)
