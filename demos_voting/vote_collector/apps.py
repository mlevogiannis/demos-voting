from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class VoteCollectorConfig(AppConfig):
    name = 'demos_voting.vote_collector'
    verbose_name = _("Vote Collector")

    def ready(self):
        super(VoteCollectorConfig, self).ready()
        import demos_voting.vote_collector.checks
        import demos_voting.vote_collector.signals
        import demos_voting.vote_collector.tasks
