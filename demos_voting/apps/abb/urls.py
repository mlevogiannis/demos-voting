# File: urls.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import include, url

from demos_voting.apps.abb import views
from demos_voting.common.utils import base32


urlpatterns = [

    url(r'^$', views.HomeView.as_view(), name='home'),

    url(r'^audit/(?:(?P<election_id>' + base32.regex + r'+)/)?$',
        views.AuditView.as_view(), name='audit'),

    url(r'^results/(?:(?P<election_id>' + base32.regex + r'+)/)?$',
        views.ResultsView.as_view(), name='results'),
]

urlpatterns_api = [

    url(r'^setup/(?P<phase>p1|p2)/$', views.ApiSetupView.as_view(), name='setup'),

    url(r'^update/$', views.ApiUpdateView.as_view(), name='update'),

    url(r'^vote/$', views.ApiVoteView.as_view(), name='vote'),

    url(r'^export/', include(views.ApiExportView.as_patterns(), namespace='export')),
]

urlpatterns_media = []

