# File: checks.py

from __future__ import absolute_import, division, print_function, unicode_literals

import importlib
import tempfile

from django.conf import settings
from django.core import checks

from requests.exceptions import RequestException


def api_check(app_configs, **kwargs):
    """Tests API for connectivity issues"""

    messages = []

    APP_DEPENDENCIES = {
        'ballot_distributor': ['election_authority'],
        'bulletin_board': ['election_authority', 'vote_collector'],
        'election_authority': ['ballot_distributor', 'bulletin_board', 'vote_collector'],
        'vote_collector': ['bulletin_board', 'election_authority'],
    }

    for local_app_label in settings.DEMOS_VOTING_APPS:
        api = importlib.import_module('demos_voting.apps.%s.utils.api' % local_app_label)
        for remote_app_label in APP_DEPENDENCIES[local_app_label]:
            if not settings.DEMOS_VOTING_API_URLS.get(remote_app_label):
                messages.append(
                    checks.Error("API URL for '%s' must not be empty." % remote_app_label,
                                 id='base.E001')
                )
            if not settings.DEMOS_VOTING_API_KEYS.get(remote_app_label):
                messages.append(
                    checks.Error("API key for '%s' must not be empty." % remote_app_label,
                                 id='base.E002')
                )
            else:
                try:
                    with api.APISession(remote_app_label) as s:
                        s.get(url='_test/')
                except RequestException as e:
                    messages.append(
                        checks.Error("Cannot connect from '%s' to '%s': %s" % (local_app_label, remote_app_label, e),
                                     id='base.E003')
                    )

    return messages


def file_storage_check(app_configs, **kwargs):
    """Tests media root for read/write access"""

    messages = []

    try:
        with tempfile.TemporaryFile(dir=settings.MEDIA_ROOT):
            pass
    except Exception as e:
        messages.append(
            checks.Error("%s" % e,
                         hint="Ensure that MEDIA_ROOT exists and is writable.",
                         id='base.E004')
        )

    return messages


def privacy_check(app_configs, **kwargs):
    """Tests for common privacy issues"""

    messages = []

    if len(settings.DEMOS_VOTING_APPS) > 1:
        messages.append(
            checks.Warning("Apps must be isolated in order to protect the voters' privacy.",
                           hint="Install each one of 'ballot_distributor', 'bulletin_board', 'election_authority' "
                                "and 'vote_collector' on different servers.",
                           id='base.W001')
        )

    return messages


def security_check(app_configs, **kwargs):
    """Tests for common security issues"""

    messages = []

    if not all(url.startswith('https://') for url in settings.DEMOS_VOTING_URLS.values()):
        messages.append(
            checks.Warning("One or more of the configured URLs do not use the HTTPS protocol.",
                           id='base.W002')
        )

    if not all(url.startswith('https://') for url in settings.DEMOS_VOTING_API_URLS.values()):
        messages.append(
            checks.Warning("One or more of the configured API URLs do not use the HTTPS protocol.",
                           id='base.W003')
        )

    return messages

