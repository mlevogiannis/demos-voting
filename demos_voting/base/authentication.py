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

from demos_voting.base.models import APIAuthNonce
from demos_voting.base.utils.api import API_AUTH_HEADER, APIUser

logger = logging.getLogger(__name__)


class APIAuthentication(BaseAuthentication):

    _scheme, _params = API_AUTH_HEADER.split()

    _credentials_regex = re.compile(_params % {
        'username': r'(?P<username>\w{1,32})',
        'nonce': r'(?P<nonce>[0-9a-f]{32})',
        'timestamp': r'(?P<timestamp>[0-9]{1,32})',
        'signature': r'(?P<signature>[0-9a-f]{64})',
    })

    def authenticate(self, request):
        header = force_bytes(request.META.get('HTTP_AUTHORIZATION', '')).split()

        if not header or header[0].lower() != self._scheme.lower():
            return None

        if len(header) != 2:
            raise AuthenticationFailed

        match = self._credentials_regex.match(header[1])
        if not match:
            raise AuthenticationFailed

        credentials = match.groupdict()
        client_username = force_text(credentials['username'])
        nonce = force_text(credentials['nonce'])
        timestamp = int(credentials['timestamp'])
        signature = force_str(credentials['signature'])

        key = settings.DEMOS_VOTING_API_KEYS.get(client_username)
        if not key:
            raise AuthenticationFailed

        if APIAuthNonce.objects.filter(username=client_username, value=nonce).exists():
            raise AuthenticationFailed

        now_timestamp = int(time.time())
        min_timestamp = now_timestamp - settings.DEMOS_VOTING_API_NONCE_TIMEOUT
        max_timestamp = now_timestamp + settings.DEMOS_VOTING_API_NONCE_TIMEOUT

        if not min_timestamp <= timestamp <= max_timestamp:
            raise AuthenticationFailed

        data_to_sign = [
            client_username,
            nonce,
            timestamp,
            request.method,
            request.path,
            request.META.get('QUERY_STRING', ''),
            request.body,
        ]

        h = hmac.new(force_bytes(key), digestmod=hashlib.sha256)
        for d in data_to_sign:
            h.update(force_bytes(d))

        if not constant_time_compare(signature, h.hexdigest()):
            raise AuthenticationFailed

        APIAuthNonce.objects.create(username=client_username, value=nonce, timestamp=timestamp)
        APIAuthNonce.objects.filter(timestamp__lt=min_timestamp).delete()

        return (APIUser(client_username), None)

