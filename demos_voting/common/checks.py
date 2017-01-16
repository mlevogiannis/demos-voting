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
        'ea':  ['bds', 'abb', 'vbb'],
        'bds': ['ea'],
        'abb': ['ea', 'vbb'],
        'vbb': ['ea', 'abb'],
    }

    for local_app_label in settings.DEMOS_VOTING_APPS:
        api = importlib.import_module('demos_voting.apps.%s.utils.api' % local_app_label)
        for remote_app_label in APP_DEPENDENCIES[local_app_label]:
            if not settings.DEMOS_VOTING_API_URLS.get(remote_app_label):
                messages.append(
                    checks.Error("API URL for '%s' must not be empty." % remote_app_label,
                                 id='common.E001')
                )
            if not settings.DEMOS_VOTING_API_KEYS.get(remote_app_label):
                messages.append(
                    checks.Error("API key for '%s' must not be empty." % remote_app_label,
                                 id='common.E002')
                )
            else:
                try:
                    with api.APISession(remote_app_label) as s:
                        s.get(url='_test/')
                except RequestException as e:
                    messages.append(
                        checks.Error("Cannot connect from '%s' to '%s': %s" % (local_app_label, remote_app_label, e),
                                     id='common.E003')
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
                         id='common.E004')
        )

    return messages


def privacy_check(app_configs, **kwargs):
    """Tests for common privacy issues"""

    messages = []

    if len(settings.DEMOS_VOTING_APPS) > 1:
        messages.append(
            checks.Warning("Apps must be isolated in order to protect the voter's privacy.",
                           hint="Install each one of [ea, bds, abb, vbb] on different servers.",
                           id='common.W001')
        )

    return messages


def security_check(app_configs, **kwargs):
    """Tests for common security issues"""

    messages = []

    if not all(url.startswith('https://') for url in settings.DEMOS_VOTING_URLS.values()):
        messages.append(
            checks.Warning("One or more of the configured URLs do not use the HTTPS protocol.",
                           id='common.W002')
        )

    if not all(url.startswith('https://') for url in settings.DEMOS_VOTING_API_URLS.values()):
        messages.append(
            checks.Warning("One or more of the configured API URLs do not use the HTTPS protocol.",
                           id='common.W003')
        )

    return messages

