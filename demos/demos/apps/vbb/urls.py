# File: urls.py

from django.conf.urls import patterns, include, url
from demos.apps.vbb import views
from demos.common.utils import api

urlpatterns = patterns('',
    url(r'^$', views.HomeView.as_view(), name='home'),
    url(r'^vote/$', views.VoteView.as_view(), name='vote'),
    url(r'^qrcode/$', views.QRCodeScannerView.as_view(), name='qrcode'),
    url(r'^(?P<election_id>[a-zA-Z0-9]+)/(?P<vote_token>[a-zA-Z0-9]+)/$', views.VoteView.as_view(), name='vote'),
)

apipatterns = [
    url(r'^manage/', include([
        url(r'^setup/$', views.SetupView.as_view(), name='setup'),
        url(r'^update/$', views.UpdateView.as_view(), name='update'),
    ], namespace='manage')),
    url(r'^auth/', include([
        url(r'^login/$', api.login, name='login'),
        url(r'^logout/$', api.logout, name='logout'),
    ], namespace='auth')),
]

