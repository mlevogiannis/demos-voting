from __future__ import absolute_import, division, print_function, unicode_literals

import rules

from django.db.models import Q

from demos_voting.bulletin_board.models import Election


@rules.predicate
def can_view_election(user, election):
    if election.visibility in (election.VISIBILITY_PUBLIC, election.VISIBILITY_HIDDEN):
        return True
    if user.is_authenticated:
        q = Q(administrators__user=user) | Q(trustees__user=user) | Q(voters__user=user)
        return Election.objects.filter(q, pk=election.pk).exists()
    return False


@rules.predicate
def can_view_ballot(user, ballot):
    q = Q(visibility=Election.VISIBILITY_PUBLIC) | Q(visibility=Election.VISIBILITY_HIDDEN)
    if user.is_authenticated:
        q |= Q(administrators__user=user) | Q(trustees__user=user) | Q(voters__user=user)
    return Election.objects.filter(q, pk=ballot.election_id).exists()


@rules.predicate
def is_election_administrator(user, election):
    return user.is_authenticated and election.administrators.filter(user=user).exists()


@rules.predicate
def is_election_trustee(user, election):
    return user.is_authenticated and election.trustees.filter(user=user).exists()


rules.add_perm('bulletin_board.can_view_election', can_view_election)
rules.add_perm('bulletin_board.can_view_ballot', can_view_ballot)
rules.add_perm('bulletin_board.can_edit_election', is_election_administrator)
rules.add_perm('bulletin_board.can_tally_election', is_election_trustee)
