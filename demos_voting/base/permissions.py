# File permissions.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.utils import six
from django.utils.encoding import force_str, python_2_unicode_compatible

from rest_framework import permissions

from demos_voting.base.utils.api import APIUser


class PermissionMeta(type):

    def __or__(self, other):
        @python_2_unicode_compatible
        class OrPermission(BasePermission):
            permission_classes = [self, other]

            def __init__(self):
                self.permissions = [permission_class() for permission_class in self.permission_classes]

            def has_permission(self, request, view):
                return any(permission.has_permission(request, view) for permission in self.permissions)

            def has_object_permission(self, request, view, obj):
                return any(permission.has_object_permission(request, view, obj) for permission in self.permissions)

            def __str__(self):
                return "(%s OR %s)" % tuple(self.permissions)

        return OrPermission

    def __and__(self, other):
        @python_2_unicode_compatible
        class AndPermission(BasePermission):
            permission_classes = [self, other]

            def __init__(self):
                self.permissions = [permission_class() for permission_class in self.permission_classes]

            def has_permission(self, request, view):
                return all(permission.has_permission(request, view) for permission in self.permissions)

            def has_object_permission(self, request, view, obj):
                return all(permission.has_object_permission(request, view, obj) for permission in self.permissions)

            def __str__(self):
                return "(%s AND %s)" % tuple(self.permissions)

        return AndPermission

    def __invert__(self):
        @python_2_unicode_compatible
        class NotPermission(BasePermission):
            permission_class = self

            def __init__(self):
                self.permission = self.permission_class()

            def has_permission(self, request, view):
                return not self.permission.has_permission(request, view)

            def has_object_permission(self, request, view, obj):
                return not self.permission.has_object_permission(request, view, obj)

            def __str__(self):
                return "(NOT %s)" % self.permission

        return NotPermission


def PermissionWrapper(permission_class):
    return type(force_str(permission_class.__name__), (six.with_metaclass(PermissionMeta, permission_class),), {})


class BasePermission(six.with_metaclass(PermissionMeta, permissions.BasePermission)):

    def __str__(self):
        return "%s" % self.__class__.__name__


class IsBallotDistributor(BasePermission):

    def has_permission(self, request, view):
        return isinstance(request.user, APIUser) and request.user.get_username() == 'ballot_distributor'


class IsBulletinBoard(BasePermission):

    def has_permission(self, request, view):
        return isinstance(request.user, APIUser) and request.user.get_username() == 'bulletin_board'


class IsElectionAuthority(BasePermission):

    def has_permission(self, request, view):
        return isinstance(request.user, APIUser) and request.user.get_username() == 'election_authority'


class IsVoteCollector(BasePermission):

    def has_permission(self, request, view):
        return isinstance(request.user, APIUser) and request.user.get_username() == 'vote_collector'

