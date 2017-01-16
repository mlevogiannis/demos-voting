# File: urls.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import include, url

from rest_framework_nested import routers

from demos_voting.apps.vbb import views
from demos_voting.common.utils import base32


urlpatterns = [
    url(r'^$', views.HomeView.as_view(), name='home'),
    url(r'^vote/$', views.VoteView.as_view(), name='vote'),
    url(r'^qrcode/$', views.QRCodeScannerView.as_view(), name='qrcode'),
    url(r'^(?P<election_id>' + base32.regex + r'+)/(?P<serial_number>[0-9]+)/(?P<tag>A|B)/(?P<credential>' +
        base32.regex + r'+)/$', views.VoteView.as_view(), name='vote'),
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

