# File: urls.py

from django.conf.urls import patterns, include, url
from demos.common.utils import api, base32cf
from demos.apps.vbb import views

urlpatterns = patterns('',
    url(r'^$', views.HomeView.as_view(), name='home'),
    url(r'^vote/$', views.VoteView.as_view(), name='vote'),
    url(r'^qrcode/$', views.QRCodeScannerView.as_view(), name='qrcode'),
    url(r'^(?P<election_id>[' + base32cf._valid + r']+)/(?P<vote_token>[' + base32cf._valid + r']+)/$', views.VoteView.as_view(), name='vote'),
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

