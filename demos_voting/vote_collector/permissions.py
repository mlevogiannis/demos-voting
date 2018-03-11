from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework.permissions import BasePermission


class DenyAll(BasePermission):
    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request, view, obj):
        return False


class CanCreateElection(BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('base.is_election_authority')


class CanUpdateElection(BasePermission):
    def has_object_permission(self, request, view, election):
        if election.state == election.STATE_BALLOT_DISTRIBUTION:
            return request.user.has_perm('base.is_ballot_distributor')
        elif election.state == election.STATE_SETUP:
            return request.user.has_perm('base.is_election_authority')
        return False


class CanCreateBallot(BasePermission):
    def has_permission(self, request, view):
        election = view.election
        return election.state == election.STATE_SETUP and request.user.has_perm('base.is_election_authority')
