# File: apps.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import AppConfig
from django.core import checks
from django.utils.translation import ugettext_lazy as _

from demos_voting.base.apps import CommonMixin
from demos_voting.election_authority.checks import ca_config_check


class AppConfig(CommonMixin, AppConfig):

    name = 'demos_voting.election_authority'
    verbose_name = _("DEMOS Voting: Election Authority")

    def ready(self):
        checks.register(ca_config_check, deploy=True)
        super(AppConfig, self).ready()

