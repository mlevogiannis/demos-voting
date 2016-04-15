# File: apps.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import AppConfig
from django.core import checks
from django.utils.translation import ugettext_lazy as _

from demos.apps.ea.checks import ca_config_check, crypto_connectivity_check
from demos.common.apps import CommonMixin


class AppConfig(CommonMixin, AppConfig):
    
    name = 'demos.apps.ea'
    verbose_name = _("Election Authority")
    
    def ready(self):
        checks.register(ca_config_check, deploy=True)
        checks.register(crypto_connectivity_check, deploy=True)
        super(AppConfig, self).ready()

