# File: urls.py

from django.conf.urls import patterns, include, url
from demos.apps.ea import views
from demos.common.utils import api

urlpatterns = patterns('',
	
	url(r'^$', views.HomeView.as_view(), name='home'),
	url(r'^create/$', views.CreateView.as_view(), name='create'),
	url(r'^status/(?:(?P<election_id>[a-zA-Z0-9]+)/)?$', views.StatusView.as_view(), name='status'),
	url(r'^center/$', views.CenterView.as_view(), name='center'),
)

apipatterns = [
	
	url(r'^auth/', include([
		url(r'^login/$', api.login, name='login'),
		url(r'^logout/$', api.logout, name='logout'),
	], namespace='auth')),
]
