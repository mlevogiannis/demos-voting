# File: urls.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import include, url

from demos_voting.apps.bds import views
from demos_voting.common.utils import base32


urlpatterns = [
    url(r'^$', views.HomeView.as_view(), name='home'),
    url(r'^manage/(?:(?P<election_id>' + base32.regex + r'+)/)?$', views.ManageView.as_view(), name='manage'),
]

urlpatterns_api = []

urlpatterns_media = []

