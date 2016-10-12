# File: urls.py

"""demos_voting URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from importlib import import_module

from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns


urlpatterns = []

for app in settings.DEMOS_VOTING_APPS:
    
    urlconf = import_module('demos_voting.apps.%s.urls' % app)
    path = r'^' + ((app + r'/') if len(settings.DEMOS_VOTING_APPS) > 1 else r'')
    
    urlpatterns += i18n_patterns(url(path, include((urlconf, app, app))))
    urlpatterns += [url(path + r'api/', include((urlconf.urlpatterns_api, app, '%s-api' % app)))]
    urlpatterns += [url(path + r'media/', include((urlconf.urlpatterns_media, app, '%s-media' % app)))]

