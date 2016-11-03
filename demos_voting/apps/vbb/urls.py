# File: urls.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import include, url

from demos_voting.apps.vbb import views
from demos_voting.common.utils import base32


urlpatterns = [

    url(r'^$', views.HomeView.as_view(), name='home'),

    url(r'^vote/$', views.VoteView.as_view(), name='vote'),

    url(r'^qrcode/$', views.QRCodeScannerView.as_view(), name='qrcode'),

    url(r'^(?P<election_id>' + base32.regex + r'+)/(?P<voter_token>'
        + base32.regex + r'+)/$', views.VoteView.as_view(), name='vote'),
]

urlpatterns_api = [

    url(r'^setup/(?P<phase>p1|p2)/$', views.ApiSetupView.as_view(), name='setup'),

    url(r'^update/$', views.ApiUpdateView.as_view(), name='update'),
]

urlpatterns_media = []

