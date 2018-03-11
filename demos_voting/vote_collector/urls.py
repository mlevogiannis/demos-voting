from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import include, url
from rest_framework_nested.routers import NestedSimpleRouter

from demos_voting.vote_collector.routers import DefaultRouter
from demos_voting.vote_collector.views import (
    APITestView, BallotViewSet, ElectionDetailView, ElectionListView, ElectionUpdateView, ElectionViewSet, HomeView,
    QRCodeView, VotingBoothSuccessView, VotingBoothView,
)

app_name = 'vote-collector'

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

            url(r'^voting-booth/', include([
                url(r'^(?P<serial_number>\d+)/(?P<tag>A|B)/', include([
                    url(r'^$', VotingBoothView.as_view(), name='short-vote-code'),
                    url(r'^(?P<credential>[-\w]+)/$', VotingBoothView.as_view(), name='long-vote-code'),
                ])),
                url(r'^success/$', VotingBoothSuccessView.as_view(), name='success'),
            ], namespace='voting-booth')),
        ])),
    ])),
    url(r'^qr-code/$', QRCodeView.as_view(), name='qr-code'),
    url(r'^api/', include([
        url(r'^', include(election_router.urls)),
        url(r'^', include(ballot_router.urls)),
        url(r'^_test/$', APITestView.as_view()),
    ], namespace='api')),
]
