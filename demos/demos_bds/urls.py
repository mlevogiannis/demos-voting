# File: urls.py

from django.conf.urls import patterns, url
from demos_bds import views

urlpatterns = patterns('',
	url(r'^api/update_or_create/$', views.UpdateOrCreateView.as_view(), name='update_or_create'),
)
