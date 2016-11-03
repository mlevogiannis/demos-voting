# File: checks.py

from __future__ import absolute_import, division, print_function, unicode_literals

import requests
import tempfile

from django.conf import settings
from django.core import checks
from django.utils.six.moves.urllib.parse import urljoin

from demos_voting.common.models import PrivateApiUser
from demos_voting.common.utils.private_api import PrivateApiAuth


def private_api_check(app_configs, **kwargs):
    """Tests private API connectivity"""

    messages = []

    for local_app in settings.DEMOS_VOTING_APPS:
        for remote_app in PrivateApiUser.APP_DEPENDENCIES[local_app]:

            try:
                r = requests.get(
                    url=urljoin(settings.DEMOS_VOTING_PRIVATE_API_URLS[remote_app], 'api/_private/test/'),
                    verify=getattr(settings, 'DEMOS_VOTING_PRIVATE_API_VERIFY_SSL', True),
                    auth=PrivateApiAuth(local_app)
                )
                r.raise_for_status()

            except Exception as e:
                messages.append(
                    checks.Error("Could not connect to %s: %s" % (remote_app, e),
                                 hint="Try running './manage.py create_private_api_users %s'." % local_app,
                                 id='common.E001')
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
                         id='common.E002')
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

    if not all(url.startswith('https://') for url in settings.DEMOS_VOTING_PRIVATE_API_URLS.values()):
        messages.append(
            checks.Warning("One or more of the configured private API URLs do not use the HTTPS protocol.",
                           id='common.W003')
        )

    return messages

