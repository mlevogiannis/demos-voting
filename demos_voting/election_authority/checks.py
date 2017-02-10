# File: checks.py

from __future__ import absolute_import, division, print_function, unicode_literals

import OpenSSL

from django.conf import settings
from django.core import checks
from django.utils.encoding import force_bytes


def ca_config_check(app_configs, **kwargs):
    """Tests CA private key and certificate configuration"""

    messages = []

    ca_cert_path = getattr(settings, 'DEMOS_VOTING_CA_CERT_FILE', '')
    ca_pkey_path = getattr(settings, 'DEMOS_VOTING_CA_PKEY_FILE', '')
    ca_pkey_passphrase = getattr(settings, 'DEMOS_VOTING_CA_PKEY_PASSPHRASE', '')

    if not (ca_pkey_path or ca_cert_path):
        messages.append(
            checks.Warning("CA is not configured, issued certificates will be self-signed.",
                           id='election_authority.I001')
        )

    else:
        try:
            with open(ca_pkey_path, 'r') as ca_pkey_file:
                ca_key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, ca_pkey_file.read(),
                                                        force_bytes(ca_pkey_passphrase))
        except Exception as e:
            messages.append(
                checks.Error("Cannot load CA private key file %s: %s" % (ca_pkey_path, e),
                             id='election_authority.E001')
            )

        try:
            with open(ca_cert_path, 'r') as ca_cert_file:
                ca_cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, ca_cert_file.read())
        except Exception as e:
            messages.append(
                checks.Error("Cannot load CA certificate file %s: %s" % (ca_cert_path, e),
                             id='election_authority.E002')
            )

    return messages

