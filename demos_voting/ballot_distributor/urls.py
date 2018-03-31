from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import include, url

from rest_framework_nested.routers import NestedSimpleRouter

from demos_voting.ballot_distributor.routers import DefaultRouter
from demos_voting.ballot_distributor.views import (
    APITestView, BallotArchiveCreateView, BallotArchiveFileDownloadView, BallotViewSet, ElectionDetailView,
    ElectionListView, ElectionUpdateView, ElectionViewSet, HomeView, VoterListCreateView,
)

app_name = 'ballot-distributor'

election_router = DefaultRouter()
election_router.register(r'elections', ElectionViewSet, 'election')
ballot_router = NestedSimpleRouter(election_router, r'elections', lookup='election')
ballot_router.register(r'ballots', BallotViewSet, 'ballot')

urlpatterns = [
    url(r'^$', HomeView.as_view(), name='home'),
    url(r'^elections/', include([
        url(r'^$', ElectionListView.as_view(), name='election-list'),
        url(r'^(?P<slug>[-\w]+)/', include([
            url(r'^$', ElectionDetailView.as_view(), name='election-detail'),
            url(r'^update/$', ElectionUpdateView.as_view(), name='election-update'),
            url(r'^ballot-archive-create/$', BallotArchiveCreateView.as_view(), name='ballot-archive-create'),
            url(r'^voter-list-create/$', VoterListCreateView.as_view(), name='voter-list-create'),
        ])),
    ])),
    url(r'^media/', include([
        url(r'^elections/(?P<slug>[-\w]+)/', include([
            url(r'^ballot-archives/(?P<uuid>[0-9a-f-]+)/ballots.zip$', BallotArchiveFileDownloadView.as_view(),
                name='ballot-archive-file'),
        ])),
    ], namespace='media')),
    url(r'^api/', include([
        url(r'^', include(election_router.urls)),
        url(r'^', include(ballot_router.urls)),
        url(r'^_test/$', APITestView.as_view()),
    ], namespace='api')),
]
