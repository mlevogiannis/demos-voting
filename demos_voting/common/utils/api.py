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

API_AUTH_SCHEME = b'API-AUTH'
API_AUTH_PARAMS = b'app="%(app_label)s",nonce="%(nonce)s",timestamp="%(timestamp)s",signature="%(signature)s"'


class APIAuth(requests.auth.AuthBase):

    auth_nonce_cls = None

    def __init__(self, server_app_label):
        self.client_app_label = self.auth_nonce_cls._meta.app_label
        self.server_app_label = server_app_label

    def __call__(self, r):
        while True:
            value = force_text(binascii.hexlify(os.urandom(16)))
            timestamp = int(time.time())
            try:
                nonce = self.auth_nonce_cls.objects.create(
                    app_label=self.server_app_label,
                    value=value,
                    timestamp=timestamp
                )
            except IntegrityError:
                continue
            else:
                break

        min_timestamp = nonce.timestamp - settings.DEMOS_VOTING_API_NONCE_TIMEOUT
        self.auth_nonce_cls.objects.filter(timestamp__lt=min_timestamp).delete()

        h = hmac.new(force_bytes(settings.DEMOS_VOTING_API_KEYS[self.server_app_label]), digestmod=hashlib.sha256)

        try:
            r_path, r_query = r.path_url.split('?', 1)
        except ValueError:
            r_path = r.path_url
            r_query = ''

        data_to_sign = [
            self.client_app_label,
            nonce.value,
            nonce.timestamp,
            r.method,
            r_path,
            r_query,
            r.body or '',
        ]

        for d in data_to_sign:
            h.update(force_bytes(d))

        r.headers[force_str('Authorization')] = force_str(API_AUTH_SCHEME + ' ' + API_AUTH_PARAMS % {
            'app_label': self.client_app_label,
            'nonce': nonce.value,
            'timestamp': nonce.timestamp,
            'signature': h.hexdigest(),
        })

        return r


class APISession(requests.Session):

    auth_cls = None

    def __init__(self, server_app_label):
        super(APISession, self).__init__()
        self.auth = self.auth_cls(server_app_label)
        self.verify = settings.DEMOS_VOTING_API_VERIFY_SSL
        self.server_app_label = server_app_label

    def request(self, method, url, *args, **kwargs):
        url = urljoin(settings.DEMOS_VOTING_API_URLS[self.server_app_label], url)
        response = super(APISession, self).request(method, url, *args, **kwargs)
        response.raise_for_status()
        return response


@python_2_unicode_compatible
class APIUser(object):

    user_permissions = None

    is_active = True
    is_superuser = False

    def __init__(self, app_label):
        self.app_label = app_label

    def get_username(self):
        return self.app_label

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    def get_group_permissions(self, obj=None):
        return set()

    def get_all_permissions(self, obj=None):
        if obj is not None:
            return set()
        return self.user_permissions.get(self.app_label, set())

    def has_perm(self, perm, obj=None):
        return perm in self.get_all_permissions(obj)

    def has_perms(self, perm_list, obj=None):
        for perm in perm_list:
            if not self.has_perm(perm, obj):
                return False
        return True

    def has_module_perms(self, module):
        for perm in self.get_all_permissions():
            if perm[:perm.index('.')] == module:
                return True
        return False

    def __str__(self):
        return self.app_label

