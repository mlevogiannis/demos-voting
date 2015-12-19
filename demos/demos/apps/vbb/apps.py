# File: apps.py

from __future__ import absolute_import, division, print_function, unicode_literals

from demos.common.conf import AppConfig as _AppConfig
from django.utils.translation import ugettext_lazy as _


class AppConfig(_AppConfig):
    
    name = 'demos.apps.vbb'
    verbose_name = _('Digital Ballot Box')
