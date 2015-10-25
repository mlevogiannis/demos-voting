# File: urls.py

from django.conf.urls import patterns, include, url
from demos.apps.bds import views
from demos.common.utils import api

urlpatterns = patterns('',
    
    url(r'^$', views.HomeView.as_view(), name='home'),
    url(r'^manage/(?P<election_id>[A-Za-z0-9])/$', views.ManageView.as_view(), name='manage'),
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

