from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import datetime
import hashlib
import hmac
import re

import pytz

from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.encoding import force_bytes
from django.utils.http import parse_http_date_safe

from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from demos_voting.base.models import HTTPSignatureKey, HTTPSignatureNonce


class HTTPSignatureAuthentication(BaseAuthentication):
    """
    Partial implementation of the latest (November 2017) `Signing HTTP
    Messages` draft. See:
    https://tools.ietf.org/id/draft-cavage-http-signatures-09.html
    https://web-payments.org/specs/source/http-signatures

    A custom extension (the `(request-nonce)` header) based on the expired
    (July 2013) `HTTP Signature Nonces` draft is used for nonces. See:
    https://web-payments.org/specs/source/http-signature-nonces

    This is the server-side implementation. For the client-side implementation,
    see `demos_voting.base.utils.api.HTTPSignatureAuth`.
    """

    generic_headers = ['(request-target)', '(request-nonce)', 'host', 'date']
    body_headers = ['content-length', 'digest']

    auth_params_re = {
        'key_id': re.compile(r'keyId="(.+?)"'),
        'algorithm': re.compile(r'algorithm="(.+?)"'),
        'headers': re.compile(r'headers="((?:\([a-z0-9!#$%&\'*+\-.^_`|~]+\) ?|[a-z0-9!#$%&\'*+\-.^_`|~]+ ?)+)"'),
        'client_id': re.compile(r'clientId="([0-9]{1,39})"'),
        'nonce': re.compile(r'nonce="([0-9]{1,10})"'),
        'signature': re.compile(r'signature="((?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?)"'),
    }

    digest_header_re = re.compile(r'^(.+?)=(.+?)(?:,(.+?)=(.+?))*$')

    def authenticate(self, request):
        now = timezone.now()
        # Parse the `authorization` header.
        auth_header = get_authorization_header(request).split(None, 1)
        if not auth_header or auth_header[0] != 'Signature':
            return None
        if len(auth_header) != 2:
            raise AuthenticationFailed
        auth_params = {}
        for name, value_re in self.auth_params_re.items():
            match = value_re.search(auth_header[1])
            if name == 'headers':
                if not match:
                    value = ['date']
                else:
                    value = match.group(1).split()
            else:
                if not match:
                    raise AuthenticationFailed
                else:
                    value = match.group(1)
            auth_params[name] = value
        # Validate the `date` header.
        date_header = request.META.get('HTTP_DATE')
        if not date_header:
            raise AuthenticationFailed
        date_timestamp = parse_http_date_safe(date_header)
        if not date_timestamp:
            raise AuthenticationFailed
        date = datetime.datetime.utcfromtimestamp(date_timestamp).replace(tzinfo=pytz.utc)
        if date < now - HTTPSignatureNonce.MAX_CLOCK_SKEW or date > now + HTTPSignatureNonce.MAX_CLOCK_SKEW:
            raise AuthenticationFailed
        # Validate the `digest` header.
        if request.body:
            digest_header = request.META.get('HTTP_DIGEST')
            if not digest_header:
                raise AuthenticationFailed
            match = self.digest_header_re.search(digest_header)
            if not match:
                raise AuthenticationFailed
            for i in range(1, match.lastindex + 1, 2):
                algorithm = match.group(i)
                digest = match.group(i + 1)
                if algorithm == 'SHA-256':
                    digest2 = base64.b64encode(hashlib.sha256(force_bytes(request.body)).digest())
                else:  # Currently only `SHA-256` is supported.
                    raise AuthenticationFailed
                if digest != digest2:
                    raise AuthenticationFailed
        # Validate the `headers` parameter.
        headers2 = list(self.generic_headers)
        if request.body:
            headers2.extend(self.body_headers)
        if set(headers2) - set(auth_params['headers']):
            raise AuthenticationFailed
        # Get the user's key.
        try:
            key_obj = HTTPSignatureKey.objects.prefetch_related('user').get(key_id=auth_params['key_id'])
        except HTTPSignatureKey.DoesNotExist:
            raise AuthenticationFailed
        # Validate the `signature` parameter.
        string_to_sign = []
        for header in auth_params['headers']:
            if header == '(request-target)':
                value = '%s %s' % (request.method.lower(), request.get_full_path())
            elif header == '(request-nonce)':
                value = '%s %s' % (auth_params['client_id'], auth_params['nonce'])
            else:
                meta_key = header.replace('-', '_').upper()
                if meta_key not in ('CONTENT_LENGTH', 'CONTENT_TYPE'):
                    meta_key = 'HTTP_%s' % meta_key
                value = request.META.get(meta_key)
            string_to_sign.append('%s: %s' % (header, value))
        string_to_sign = '\n'.join(string_to_sign)
        if auth_params['algorithm'] == 'hmac-sha256':
            h = hmac.new(force_bytes(key_obj.key), force_bytes(string_to_sign), digestmod=hashlib.sha256)
            signature2 = base64.b64encode(h.digest())
        else:  # Currently only `hmac-sha256` is supported.
            raise AuthenticationFailed
        if not constant_time_compare(auth_params['signature'], signature2):
            raise AuthenticationFailed
        # Validate the `nonce` parameter.
        nonce_obj, created = HTTPSignatureNonce.objects.get_or_create(
            key=key_obj,
            client_id=auth_params['client_id'],
            nonce=auth_params['nonce'],
            date__gte=now - HTTPSignatureNonce.MAX_CLOCK_SKEW,
            date__lte=now + HTTPSignatureNonce.MAX_CLOCK_SKEW,
            defaults={'date': date},
        )
        if not created:
            raise AuthenticationFailed
        return key_obj.user, None

    def authenticate_header(self, request):
        return 'Signature realm="api"'
