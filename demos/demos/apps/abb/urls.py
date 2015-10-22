# File: urls.py

from django.conf.urls import patterns, include, url
from demos.common.utils import api
from demos.apps.abb import views

urlpatterns = patterns('',
    url(r'^$', views.HomeView.as_view(), name='home'),
    url(r'^audit/(?:(?P<election_id>[a-zA-Z0-9]+)/)?$', views.AuditView.as_view(), name='audit'),
    url(r'^results/(?:(?P<election_id>[a-zA-Z0-9]+)/)?$', views.ResultsView.as_view(), name='results'),
)

apipatterns = [
    url(r'^manage/', include([
        url(r'^setup/$', views.SetupView.as_view(), name='setup'),
        url(r'^update/$', views.UpdateView.as_view(), name='update'),
    ], namespace='manage')),
    url(r'^command/', include([
        url(r'^vote/$', views.VoteView.as_view(), name='vote'),
    ], namespace='command')),
    url(r'^auth/', include([
        url(r'^login/$', api.login, name='login'),
        url(r'^logout/$', api.logout, name='logout'),
    ], namespace='auth')),
    
    url(r'^export/', include(views.ExportView.urlpatterns(), namespace='export')),
]

