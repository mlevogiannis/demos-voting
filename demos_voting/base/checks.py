from __future__ import absolute_import, division, print_function, unicode_literals

import tempfile

from allauth.account import app_settings as account_settings
from allauth.socialaccount import app_settings as socialaccount_settings

from django.conf import settings
from django.core.checks import Error, Warning, register

from demos_voting.base.utils import app_labels, installed_app_labels


@register(deploy=True)
def demos_voting_settings_check(app_configs, **kwargs):
    """
    Check for DEMOS Voting configuration issues.
    """
    messages = []
    if len(installed_app_labels) > 1:
        warning = Warning(
            id='base.W001',
            msg="DEMOS Voting applications must be isolated in order to protect the voters' privacy.",
            hint="Install each application (%s) on a different server." % ", ".join(app_labels),
        )
        messages.append(warning)
    for app_label in app_labels:
        if not settings.DEMOS_VOTING_URLS.get(app_label):
            error = Error(
                id='base.E001',
                msg="URL for '%s' must not be empty." % app_label,
                hint="Configure the DEMOS_VOTING_URLS setting.",
            )
            messages.append(error)
        if not settings.DEMOS_VOTING_URLS[app_label].startswith('https://'):
            warning = Warning(
                id='base.W002',
                msg="URL for '%s' does not use HTTPS." % app_label,
                hint="Configure the '%s' server to use HTTPS." % app_label,
            )
            messages.append(warning)
        if settings.DEMOS_VOTING_INTERNAL_URLS is not None:
            if not settings.DEMOS_VOTING_INTERNAL_URLS.get(app_label):
                error = Error(
                    id='base.E002',
                    msg="Internal URL for '%s' must not be empty." % app_label,
                    hint="Configure the DEMOS_VOTING_INTERNAL_URLS setting.",
                )
                messages.append(error)
            if not settings.DEMOS_VOTING_INTERNAL_URLS[app_label].startswith('https://'):
                warning = Warning(
                    id='base.W003',
                    msg="Internal URL for '%s' does not use HTTPS." % app_label,
                    hint="Configure the '%s' server to use HTTPS." % app_label,
                )
                messages.append(warning)
    return messages


@register
def media_settings_check(app_configs, **kwargs):
    """
    Check for MEDIA_URL and MEDIA_ROOT configuration issues.
    """
    messages = []
    if settings.MEDIA_URL:
        error = Error(
            id='base.E003',
            msg="The MEDIA_URL setting must be empty.",
            hint="The web server must not serve the files in MEDIA_ROOT.",
        )
        messages.append(error)
    try:
        with tempfile.TemporaryFile(dir=settings.MEDIA_ROOT):
            pass
    except Exception as e:
        error = Error(
            id='base.E004',
            msg="%s" % e,
            hint="Ensure that MEDIA_ROOT exists and is writable.",
        )
        messages.append(error)
    return messages


@register
def account_settings_check(app_configs, **kwargs):
    """
    Check for account configuration issues.
    """
    messages = []
    if not account_settings.EMAIL_REQUIRED:
        error = Error(
            id='base.E005',
            msg="ACCOUNT_EMAIL_REQUIRED setting must be set to True.",
        )
        messages.append(error)
    if account_settings.EMAIL_VERIFICATION != 'mandatory':
        error = Error(
            id='base.E006',
            msg="ACCOUNT_EMAIL_VERIFICATION setting must be set to 'mandatory'.",
        )
        messages.append(error)
    if not account_settings.UNIQUE_EMAIL:
        error = Error(
            id='base.E007',
            msg="ACCOUNT_UNIQUE_EMAIL setting must be set to True.",
        )
        messages.append(error)
    if not all(username in account_settings.USERNAME_BLACKLIST for username in app_labels):
        error = Error(
            id='base.E008',
            msg="ACCOUNT_USERNAME_BLACKLIST setting must contain %s." % ", ".join("'%s'" % s for s in app_labels),
        )
        messages.append(error)
    if not socialaccount_settings.EMAIL_REQUIRED:
        error = Error(
            id='base.E009',
            msg="SOCIALACCOUNT_EMAIL_REQUIRED setting must be set to True.",
        )
        messages.append(error)
    if not socialaccount_settings.EMAIL_VERIFICATION:
        error = Error(
            id='base.E010',
            msg="SOCIALACCOUNT_EMAIL_VERIFICATION setting must be set to True.",
        )
        messages.append(error)
    if not socialaccount_settings.QUERY_EMAIL:
        error = Error(
            id='base.E011',
            msg="SOCIALACCOUNT_QUERY_EMAIL setting must be set to True.",
        )
        messages.append(error)
    return messages
