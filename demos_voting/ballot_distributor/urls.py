# File: urls.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import include, url

from rest_framework_nested import routers

from demos_voting.ballot_distributor import views
from demos_voting.base.utils import base32


urlpatterns = [
    url(r'^$', views.HomeView.as_view(), name='home'),
    url(r'^manage/(?:(?P<election_id>' + base32.regex + r'+)/)?$', views.ManageView.as_view(), name='manage'),
]

# -----------------------------------------------------------------------------

election_router = routers.DefaultRouter()
election_router.register(r'elections', views.ElectionViewSet, 'election')

ballot_router = routers.NestedSimpleRouter(election_router, r'elections', lookup='election')
ballot_router.register(r'ballots', views.BallotViewSet, 'ballot')

urlpatterns_api = [
    url(r'^', include(election_router.urls)),
    url(r'^', include(ballot_router.urls)),
    url(r'^_test/$', views.TestAPIView.as_view()),
]

# -----------------------------------------------------------------------------

urlpatterns_media = []

