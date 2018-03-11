from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class BulletinBoardConfig(AppConfig):
    name = 'demos_voting.bulletin_board'
    verbose_name = _("Bulletin Board")

    def ready(self):
        super(BulletinBoardConfig, self).ready()
        import demos_voting.bulletin_board.checks
        import demos_voting.bulletin_board.signals
        import demos_voting.bulletin_board.tasks
