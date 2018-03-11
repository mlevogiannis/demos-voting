from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework.permissions import BasePermission


class DenyAll(BasePermission):
    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request, view, obj):
        return False
