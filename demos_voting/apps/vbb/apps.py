# File: apps.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

from demos_voting.common.apps import CommonMixin


class AppConfig(CommonMixin, AppConfig):
    
    name = 'demos_voting.apps.vbb'
    verbose_name = _("Virtual Ballot Box")

