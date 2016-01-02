# File: urls.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import include, url

from demos.apps.ea import views
from demos.common.utils import base32


urlpatterns = [
    
    url(r'^$', views.HomeView.as_view(), name='home'),
    
    url(r'^create/$', views.CreateView.as_view(), name='create'),
    
    url(r'^status/(?:(?P<election_id>' + base32.regex + r'+)/)?$',
        views.StatusView.as_view(), name='status'),
    
    url(r'^center/$', views.CenterView.as_view(), name='center'),
]

apipatterns = [
    
    url(r'^updatestate/$', views.ApiUpdateStateView.as_view(), name='updatestate'),
    
    url(r'^crypto/(?P<command>add_com|add_decom|complete_zk|verify_com)/$',
        views.ApiCryptoView.as_view(), name='crypto'),
]

