"""demos_voting URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import apps
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic.base import RedirectView

from demos_voting.base.utils import installed_app_labels
from demos_voting.base.views import ProfileView, SetLanguageAndTimezoneView

urlpatterns = [
    url(r'^account/', include([
        url(r'^$', RedirectView.as_view(pattern_name='account_profile')),
        url(r'^profile/$', ProfileView.as_view(), name='account_profile'),
        url(r'^set-language-and-timezone/$', SetLanguageAndTimezoneView.as_view(), name='set-language-and-timezone'),
        url(r'^', include('allauth.urls')),

    ])),
    url(r'^admin/', admin.site.urls),
]

for app_label in installed_app_labels:
    url_path = r'^%s/' % app_label.replace('_', '-') if len(installed_app_labels) > 1 else r'^'
    urlpatterns.append(url(url_path, include('demos_voting.%s.urls' % app_label)))

if settings.DEBUG:
    if apps.is_installed('debug_toolbar'):
        import debug_toolbar

        urlpatterns.append(url(r'^__debug__/', include(debug_toolbar.urls)))
