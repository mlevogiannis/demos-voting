# File: urls.py

from django.conf.urls import patterns, url
from demos_ea import views

urlpatterns = patterns('',
	url(r'^$', views.HomeView.as_view(), name='home'),
	url(r'^define/$', views.DefineView.as_view(), name='define'),
	url(r'^manage/(?P<election_id>[a-zA-Z0-9]+)/$', views.ManageView.as_view(), name='manage'),
	
	url(r'^manage/$', views.ManageView.as_view(), name='progress'),
)
