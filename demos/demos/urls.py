# File: urls.py

"""demos URL Configuration

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

from importlib import import_module

from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin

app_name = '%s' % settings.DEMOS_MAIN
urlconfig = import_module('demos.apps.%s.urls' % settings.DEMOS_MAIN)

urlpatterns = i18n_patterns(
    url(r'^', include(urlconfig, namespace=app_name, app_name=app_name)),
)

urlpatterns += [
	url(r'^api/', include(urlconfig.apipatterns, namespace='api', app_name=app_name)),
]
