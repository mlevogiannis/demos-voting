# File permission.py

from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework import permissions

from demos_voting.base.utils.api import APIUser


class IsBallotDistributor(permissions.BasePermission):

    def has_permission(self, request, view):
        return isinstance(request.user, APIUser) and request.user.get_username() == 'ballot_distributor'


class IsBulletinBoard(permissions.BasePermission):

    def has_permission(self, request, view):
        return isinstance(request.user, APIUser) and request.user.get_username() == 'bulletin_board'


class IsElectionAuthority(permissions.BasePermission):

    def has_permission(self, request, view):
        return isinstance(request.user, APIUser) and request.user.get_username() == 'election_authority'


class IsVoteCollector(permissions.BasePermission):

    def has_permission(self, request, view):
        return isinstance(request.user, APIUser) and request.user.get_username() == 'vote_collector'

