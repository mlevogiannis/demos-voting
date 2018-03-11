from __future__ import absolute_import, division, print_function, unicode_literals

import requests

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from django.conf import settings
from django.core.checks import Error, Warning, register
from django.utils.encoding import force_bytes

from demos_voting.election_authority.utils.api import (
    BallotDistributorAPISession, BulletinBoardAPISession, VoteCollectorAPISession,
)


@register(deploy=True)
def api_connectivity_check(app_configs, **kwargs):
    """
    Check for API connectivity issues.
    """
    messages = []
    for api_session_class in [BallotDistributorAPISession, BulletinBoardAPISession, VoteCollectorAPISession]:
        with api_session_class() as s:
            try:
                r = s.get('_test/')
                r.raise_for_status()
                r = s.post('_test/', json={'key': 'value'})
                r.raise_for_status()
            except requests.exceptions.RequestException as e:
                error = Error(
                    id='election_authority.E001',
                    msg="Connection to '%s' failed: %s" % (api_session_class.server_username, e),
                    hint="If this is an authentication issue, use the 'createsystemusers' management command to "
                         "create/update the system's users.",
                )
                messages.append(error)
    return messages


@register(deploy=True)
def demos_voting_settings_check(app_configs, **kwargs):
    """
    Check for DEMOS Voting configuration issues.
    """
    messages = []
    issuer_private_key_path = settings.DEMOS_VOTING_CERTIFICATE_ISSUER.get('private_key_path', '')
    issuer_certificate_path = settings.DEMOS_VOTING_CERTIFICATE_ISSUER.get('certificate_path', '')
    if not (issuer_private_key_path or issuer_certificate_path):
        warning = Warning(
            id='election_authority.W001',
            msg="A certificate issuer is not configured, election certificates will be self-signed.",
            hint="Configure the certificate issuer's private key and certificate.",
        )
        messages.append(warning)
    else:
        try:
            with open(issuer_private_key_path, 'rb') as issuer_private_key_file:
                issuer_private_key_password = settings.DEMOS_VOTING_CERTIFICATE_ISSUER('private_key_password', '')
                issuer_private_key = load_pem_private_key(
                    data=issuer_private_key_file.read(),
                    password=force_bytes(issuer_private_key_password) or None,
                    backend=default_backend(),
                )
        except Exception as e:
            error = Error(
                id='election_authority.E002',
                msg="Cannot load the certificate issuer's private key: %s" % e,
            )
            messages.append(error)
        try:
            with open(issuer_certificate_path, 'rb') as issuer_certificate_file:
                issuer_certificate = x509.load_pem_x509_certificate(
                    data=issuer_certificate_file.read(),
                    backend=default_backend(),
                )
        except Exception as e:
            error = Error(
                id='election_authority.E003',
                msg="Cannot load the certificate issuer's certificate: %s" % e,
            )
            messages.append(error)
    return messages
