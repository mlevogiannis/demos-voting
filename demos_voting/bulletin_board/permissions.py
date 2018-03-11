from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework.permissions import BasePermission


class DenyAll(BasePermission):
    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request, view, obj):
        return False


class CanViewElection(BasePermission):
    def has_object_permission(self, request, view, election):
        permissions = [
            'base.is_ballot_distributor',
            'base.is_election_authority',
            'base.is_vote_collector',
            'bulletin_board.can_view_election',
        ]
        return any(request.user.has_perm(perm, election) for perm in permissions)


class CanCreateElection(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('base.is_election_authority')


class CanUpdateElection(BasePermission):
    def has_object_permission(self, request, view, election):
        if election.state == election.STATE_BALLOT_DISTRIBUTION:
            return request.user.has_perm('base.is_ballot_distributor')
        elif election.state == election.STATE_SETUP:
            return request.user.has_perm('base.is_election_authority')
        elif election.state == election.STATE_VOTING:
            return request.user.has_perm('base.is_vote_collector')
        elif election.state == election.STATE_TALLY:
            return request.user.has_perm('bulletin_board.can_tally_election', election)
        return False


class CanCreateTrustee(BasePermission):
    def has_object_permission(self, request, view, election):
        return election.state == election.STATE_SETUP and request.user.has_perm('base.is_election_authority')


class CanCreateVoter(BasePermission):
    def has_object_permission(self, request, view, election):
        return (election.state == election.STATE_BALLOT_DISTRIBUTION and
                request.user.has_perm('base.is_ballot_distributor'))


class CanViewBallot(BasePermission):
    def has_permission(self, request, view):
        election = view.election
        return request.user.has_perm('bulletin_board.can_view_election', election)

    def has_object_permission(self, request, view, ballot):
        permissions = [
            'base.is_ballot_distributor',
            'base.is_election_authority',
            'base.is_vote_collector',
            'bulletin_board.can_view_ballot',
        ]
        return any(request.user.has_perm(perm, ballot) for perm in permissions)


class CanCreateBallot(BasePermission):
    def has_permission(self, request, view):
        election = view.election
        return election.state == election.STATE_SETUP and request.user.has_perm('base.is_election_authority')


class CanUpdateBallot(BasePermission):
    def has_object_permission(self, request, view, ballot):
        election = view.election
        if election.state == election.STATE_VOTING:
            return request.user.has_perm('base.is_vote_collector')
        elif election.state == election.STATE_TALLY:
            return request.user.has_perm('bulletin_board.can_tally_election', election)
        return False
