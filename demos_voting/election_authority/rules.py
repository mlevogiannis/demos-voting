from __future__ import absolute_import, division, print_function, unicode_literals

import rules


@rules.predicate
def is_election_administrator(user, election):
    return user.is_authenticated and election.administrators.filter(user=user).exists()


rules.add_perm('election_authority.can_create_election', rules.is_authenticated)
rules.add_perm('election_authority.can_view_election', is_election_administrator)
rules.add_perm('election_authority.can_edit_election', is_election_administrator)
