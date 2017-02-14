# File: api.py

from __future__ import absolute_import, division, print_function, unicode_literals

import binascii
import hashlib
import hmac
import os
import time

import requests

from django.conf import settings
from django.db import IntegrityError
from django.utils.encoding import force_bytes, force_str, force_text, python_2_unicode_compatible
from django.utils.six.moves.urllib.parse import urljoin

from demos_voting.base.models import APIAuthNonce


API_AUTH_HEADER = (
    b'API-Auth username="%(username)s",nonce="%(nonce)s",timestamp="%(timestamp)s",signature="%(signature)s"'
)


class APIAuth(requests.auth.AuthBase):

    def __init__(self, client_username, server_username):
        self._client_username = client_username
        self._server_username = server_username

    def __call__(self, r):
        while True:
            value = force_text(binascii.hexlify(os.urandom(16)))
            timestamp = int(time.time())
            try:
                nonce = APIAuthNonce.objects.create(
                    username=self._server_username,
                    value=value,
                    timestamp=timestamp
                )
            except IntegrityError:
                continue
            else:
                break

        APIAuthNonce.objects.filter(timestamp__lt=nonce.timestamp-settings.DEMOS_VOTING_API_NONCE_TIMEOUT).delete()

        try:
            r_path, r_query = r.path_url.split('?', 1)
        except ValueError:
            r_path = r.path_url
            r_query = ''

        data_to_sign = [
            self._client_username,
            nonce.value,
            nonce.timestamp,
            r.method,
            r_path,
            r_query,
            r.body or '',
        ]

        h = hmac.new(force_bytes(settings.DEMOS_VOTING_API_KEYS[self._server_username]), digestmod=hashlib.sha256)
        for d in data_to_sign:
            h.update(force_bytes(d))

        r.headers[force_str('Authorization')] = force_str(API_AUTH_HEADER % {
            'username': self._client_username,
            'nonce': nonce.value,
            'timestamp': nonce.timestamp,
            'signature': h.hexdigest(),
        })

        return r


class APISession(requests.Session):

    def __init__(self, client_username, server_username):
        super(APISession, self).__init__()
        self._client_username = client_username
        self._server_username = server_username
        self.auth = APIAuth(client_username, server_username)
        self.verify = settings.DEMOS_VOTING_API_VERIFY_SSL

    def request(self, method, url, *args, **kwargs):
        url = urljoin(settings.DEMOS_VOTING_API_URLS[self._server_username], url)
        response = super(APISession, self).request(method, url, *args, **kwargs)
        response.raise_for_status()
        return response


@python_2_unicode_compatible
class APIUser(object):

    is_active = True
    is_superuser = False

    def __init__(self, username):
        self.username = username

    def get_username(self):
        return self.username

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    def __str__(self):
        return self.username

