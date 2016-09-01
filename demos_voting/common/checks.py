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
                    url=urljoin(settings.DEMOS_VOTING_API_URLS[remote_app], 'api/_private/test/'),
                    verify=getattr(settings, 'DEMOS_VOTING_PRIVATE_API_VERIFY_SSL', True),
                    auth=PrivateApiAuth(local_app, remote_app)
                )
                r.raise_for_status()
            
            except Exception as e:
                messages.append(
                    checks.Error("Could not connect to %s: %s" % (remote_app, e),
                                 hint="Try running ./manage.py createprivateapiusers %s." % local_app,
                                 id='common.E001')
                )
    
    return messages


def file_storage_check(app_configs, **kwargs):
    """Tests data dir for read/write access"""
    
    messages = []
    
    try:
        with tempfile.TemporaryFile(dir=settings.DEMOS_VOTING_DATA_DIR):
            pass
    except Exception as e:
        messages.append(
            checks.Error("Data directory %s: %s" % e,
                         hint="Ensure that the directory exists and is writable.",
                         id='common.E002')
        )
    
    return messages


def security_check(app_configs, **kwargs):
    """Tests for common security issues"""
    
    messages = []
    
    if settings.DEMOS_VOTING_APPS > 1:
        messages.append(
            checks.Warning("Apps must be isolated in order to support voter privacy.",
                           hint="Install each one of (ea, bds, abb, vbb) to different servers.",
                           id='common.W001')
        )
    
    urls = settings.DEMOS_VOTING_URLS.values() + settings.DEMOS_VOTING_PRIVATE_API_URLS.values()
    
    if not all(url.startswith('https://') for url in urls):
        messages.append(
            checks.Warning("One or more of the configured URLs do not use the HTTPS protocol.",
                           id='common.W002')
        )
    
    return messages

