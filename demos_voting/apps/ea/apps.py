# File: apps.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import AppConfig
from django.core import checks
from django.utils.translation import ugettext_lazy as _

from demos_voting.apps.ea.checks import ca_config_check
from demos_voting.common.apps import CommonMixin


class AppConfig(CommonMixin, AppConfig):

    name = 'demos_voting.apps.ea'
    verbose_name = _("Election Authority")

    def ready(self):
        checks.register(ca_config_check, deploy=True)
        super(AppConfig, self).ready()

