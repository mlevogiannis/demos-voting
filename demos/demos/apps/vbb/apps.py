# File: apps.py

from __future__ import division, unicode_literals

from django.apps import AppConfig as _AppConfig
from django.utils.translation import ugettext_lazy as _


class AppConfig(_AppConfig):
    name = 'demos.apps.vbb'
    verbose_name = _('Digital Ballot Box')
