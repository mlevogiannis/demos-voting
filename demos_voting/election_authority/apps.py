from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ElectionAuthorityConfig(AppConfig):
    name = 'demos_voting.election_authority'
    verbose_name = _("Election Authority")

    def ready(self):
        super(ElectionAuthorityConfig, self).ready()
        import demos_voting.election_authority.checks
        import demos_voting.election_authority.signals
        import demos_voting.election_authority.tasks
