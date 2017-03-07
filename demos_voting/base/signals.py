# File signals.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings


def prevent_election_deletion(sender, **kwargs):
    assert settings.DEBUG, "Elections should not be deleted in production, in order to avoid id reuse."
