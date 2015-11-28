# File: urls.py

from django.conf.urls import include, url
from demos.common.utils import base32cf
from demos.apps.ea import views


urlpatterns = [
    url(r'^$', views.HomeView.as_view(), name='home'),
    url(r'^create/$', views.CreateView.as_view(), name='create'),
    url(r'^status/(?:(?P<election_id>[' + base32cf._valid_re + r']+)/)?$', \
        views.StatusView.as_view(), name='status'),
    url(r'^center/$', views.CenterView.as_view(), name='center'),
]

apipatterns = [
    url(r'^updatestate/$', views.UpdateStateView.as_view(), name='updatestate'),
    url(r'^crypto/(?P<command>add_com|add_decom|complete_zk|verify_com)/$', \
        views.CryptoToolsView.as_view(), name='crypto'),
]

