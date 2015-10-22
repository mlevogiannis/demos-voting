# File: apps.py

from django.apps import AppConfig as _AppConfig
from django.utils.translation import ugettext_lazy as _


class AppConfig(_AppConfig):
    name = 'demos.apps.bds'
    verbose_name = _('Ballot Distribution Center')
