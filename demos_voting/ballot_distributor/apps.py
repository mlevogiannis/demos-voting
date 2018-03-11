from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class BallotDistributorConfig(AppConfig):
    name = 'demos_voting.ballot_distributor'
    verbose_name = _("Ballot Distributor")

    def ready(self):
        super(BallotDistributorConfig, self).ready()
        import demos_voting.ballot_distributor.checks
        import demos_voting.ballot_distributor.signals
        import demos_voting.ballot_distributor.tasks
