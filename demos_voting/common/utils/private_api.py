# File: private_api.py

from __future__ import absolute_import, division, print_function, unicode_literals

import binascii
import hashlib
import hmac
import logging
import os
import time

import requests

from django.apps import apps
from django.conf import settings
from django.db import transaction
from django.utils.encoding import force_bytes, force_str, force_text

logger = logging.getLogger(__name__)

PRIVATE_API_AUTH_SCHEME = 'DEMOS_VOTING_PRIVATE_API'
PRIVATE_API_AUTH_PARAMS = 'app_label="%(app_label)s",timestamp="%(timestamp)s",nonce="%(nonce)s",digest="%(digest)s"'


class PrivateApiAuth(requests.auth.AuthBase):

    def __init__(self, local_app_label):

        self.local_app_label = local_app_label

    def __call__(self, r):

        # Get remote app's label from the request URL.

        urls = settings.DEMOS_VOTING_PRIVATE_API_URLS

        try:
            remote_app_label = next(
                app_label for app_label, url in urls.items() if force_text(r.url).startswith(force_text(url))
            )
        except StopIteration:
            raise ValueError("Request URL not in DEMOS_VOTING_PRIVATE_API_URLS: %s" % r.url)

        # Generate a unique nonce - timestamp pair.

        app_config = apps.get_app_config(self.local_app_label)

        PrivateApiUser = app_config.get_model('PrivateApiUser')
        PrivateApiNonce = app_config.get_model('PrivateApiNonce')

        with transaction.atomic():

            user = PrivateApiUser.objects.select_for_update().get(app_label=remote_app_label)
            nonces = user.nonces.filter(type=PrivateApiNonce.TYPE_LOCAL)

            # Get the current timestamp only after locking the user object.
            timestamp = int(time.time())

            # Remove expired local nonces.
            nonces.filter(timestamp__lt=timestamp).delete()

            nonce = None
            while nonce is None or nonces.filter(nonce=nonce, timestamp=timestamp).exists():
                nonce = force_text(binascii.hexlify(os.urandom(16)))

        # Compute the request's digest.

        try:
            r_path, r_query = r.path_url.split('?', 1)
        except ValueError:
            r_path = r.path_url
            r_query = ''

        elements = [
            self.local_app_label,
            timestamp,
            nonce,
            r.method,
            r_path,
            r_query,
            r.body or '',
        ]

        h = hmac.new(force_bytes(user.preshared_key), digestmod=hashlib.sha512)
        for e in elements:
            h.update(force_bytes(e))

        # Prepare the HTTP Authorization header.

        r.headers[force_str('Authorization')] = force_str(PRIVATE_API_AUTH_SCHEME + ' ' + PRIVATE_API_AUTH_PARAMS % {
            'app_label': self.local_app_label,
            'timestamp': timestamp,
            'nonce': nonce,
            'digest': h.hexdigest()
        })

        return r

