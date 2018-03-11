from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework.pagination import LimitOffsetPagination as BaseLimitOffsetPagination


class LimitOffsetPagination(BaseLimitOffsetPagination):
    default_limit = 10
    max_limit = 10
