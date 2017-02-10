# File: authentication.py

from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib
import hmac
import logging
import re
import time

from django.conf import settings
from django.utils.crypto import constant_time_compare
from django.utils.encoding import force_bytes, force_str, force_text

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from demos_voting.base.utils.api import API_AUTH_PARAMS, API_AUTH_SCHEME

logger = logging.getLogger(__name__)


class APIAuthentication(BaseAuthentication):

    user_cls = None
    auth_nonce_cls = None

    credentials_re = re.compile(API_AUTH_PARAMS % {
        'app_label': r'(?P<app_label>%s)' % r'|'.join([k for k, v in settings.DEMOS_VOTING_API_KEYS.items() if v]),
        'nonce': r'(?P<nonce>[0-9a-f]{32})',
        'timestamp': r'(?P<timestamp>[0-9]+)',
        'signature': r'(?P<signature>[0-9a-f]{64})',
    })

    def authenticate(self, request):
        header = force_bytes(request.META.get('HTTP_AUTHORIZATION', '')).split()

        if not header or header[0].lower() != API_AUTH_SCHEME.lower():
            return None

        if len(header) != 2:
            raise AuthenticationFailed

        match = self.credentials_re.match(header[1])
        if not match:
            raise AuthenticationFailed

        credentials = match.groupdict()
        client_app_label = force_text(credentials['app_label'])
        nonce = force_text(credentials['nonce'])
        timestamp = int(credentials['timestamp'])
        signature = force_str(credentials['signature'])

        key = settings.DEMOS_VOTING_API_KEYS.get(client_app_label)
        if not key:
            raise AuthenticationFailed

        if self.auth_nonce_cls.objects.filter(app_label=client_app_label, value=nonce).exists():
            raise AuthenticationFailed

        now_timestamp = int(time.time())
        min_timestamp = now_timestamp - settings.DEMOS_VOTING_API_NONCE_TIMEOUT
        max_timestamp = now_timestamp + settings.DEMOS_VOTING_API_NONCE_TIMEOUT

        if not min_timestamp <= timestamp <= max_timestamp:
            raise AuthenticationFailed

        h = hmac.new(force_bytes(key), digestmod=hashlib.sha256)

        data_to_sign = [
            client_app_label,
            nonce,
            timestamp,
            request.method,
            request.path,
            request.META.get('QUERY_STRING', ''),
            request.body,
        ]

        for d in data_to_sign:
            h.update(force_bytes(d))

        if not constant_time_compare(signature, h.hexdigest()):
            raise AuthenticationFailed

        self.auth_nonce_cls.objects.create(app_label=client_app_label, value=nonce, timestamp=timestamp)
        self.auth_nonce_cls.objects.filter(timestamp__lt=min_timestamp).delete()

        return (self.user_cls(client_app_label), None)

