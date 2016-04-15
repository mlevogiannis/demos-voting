# File: apps.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

from demos.common.apps import CommonMixin


class AppConfig(CommonMixin, AppConfig):
    
    name = 'demos.apps.abb'
    verbose_name = _("Audit and Results")

