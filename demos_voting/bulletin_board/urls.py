from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import include, url

from rest_framework_nested.routers import NestedSimpleRouter

from demos_voting.bulletin_board.routers import DefaultRouter
from demos_voting.bulletin_board.views import (
    APITestView, BallotDetailView, BallotViewSet, ElectionCertificateDownloadView, ElectionDetailView,
    ElectionListView, ElectionUpdateView, ElectionViewSet, HomeView, TallyView,
)

app_name = 'bulletin-board'

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
            url(r'^tally/$', TallyView.as_view(), name='tally'),
            url(r'^ballots/(?P<serial_number>\d+)/$', BallotDetailView.as_view(), name='ballot-detail'),
        ])),
    ])),
    url(r'^media/', include([
        url(r'^elections/(?P<slug>[-\w]+)/', include([
            url(r'^certificate.pem', ElectionCertificateDownloadView.as_view(), name='election-certificate'),
        ])),
    ], namespace='media')),
    url(r'^api/', include([
        url(r'^', include(election_router.urls)),
        url(r'^', include(ballot_router.urls)),
        url(r'^_test/$', APITestView.as_view()),
    ], namespace='api')),
]
