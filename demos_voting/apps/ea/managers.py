# File: managers.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.db import models


class TrusteeManager(models.Manager):

    def get_by_natural_key(self, election_id, email):

        election_manager = self.model._meta.get_field('election').related_model.objects.db_manager(self.db)
        election = election_manager.get_by_natural_key(election_id)

        return self.get(election=election, email=email)

