from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import AppConfig


class BaseConfig(AppConfig):
    name = 'demos_voting.base'
    verbose_name = "DEMOS Voting"

    def ready(self):
        super(BaseConfig, self).ready()
        import demos_voting.base.checks
        import demos_voting.base.signals
        import demos_voting.base.tasks
