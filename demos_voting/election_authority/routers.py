from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework import routers

from demos_voting.election_authority.views import APIRootView


class DefaultRouter(routers.DefaultRouter):
    APIRootView = APIRootView
