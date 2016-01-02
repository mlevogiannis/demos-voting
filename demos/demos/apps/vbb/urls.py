# File: urls.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import include, url

from demos.apps.vbb import views
from demos.common.utils import base32cf


urlpatterns = [
    
    url(r'^$', views.HomeView.as_view(), name='home'),
    
    url(r'^vote/$', views.VoteView.as_view(), name='vote'),
    
    url(r'^qrcode/$', views.QRCodeScannerView.as_view(), name='qrcode'),
    
    url(r'^(?P<election_id>' + base32cf.regex + r'+)/(?P<voter_token>'
        + base32cf.regex + r'+)/$', views.VoteView.as_view(), name='vote'),
]

apipatterns = [
    
    url(r'^setup/(?P<phase>p1|p2)/$', views.ApiSetupView.as_view(), name='setup'),
    
    url(r'^update/$', views.ApiUpdateView.as_view(), name='update'),
]

