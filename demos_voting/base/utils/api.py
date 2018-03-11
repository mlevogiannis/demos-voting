from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import calendar
import hashlib
import hmac
import os

import requests

from django.conf import settings
from django.utils import timezone
from django.utils.http import http_date
from django.utils.encoding import force_bytes, force_text

from six.moves.urllib.parse import urljoin, urlparse

from demos_voting.base.models import HTTPSignatureKey, HTTPSignatureNonce
from demos_voting.base.utils.compat import int_from_bytes


class HTTPSignatureAuth(requests.auth.AuthBase):
    """
    Partial implementation of the latest (November 2017) `Signing HTTP
    Messages` draft. See:
    https://tools.ietf.org/id/draft-cavage-http-signatures-09.html
    https://web-payments.org/specs/source/http-signatures

    A custom extension (the `(request-nonce)` header) based on the expired
    (July 2013) `HTTP Signature Nonces` draft is used for nonces. See:
    https://web-payments.org/specs/source/http-signature-nonces

    This is the client-side implementation. For the server-side implementation,
    see `demos_voting.base.authentication.HTTPSignatureAuthentication`.
    """

    generic_headers = ['(request-target)', '(request-nonce)', 'host', 'date']
    body_headers = ['content-length', 'digest']

    def __init__(self, client_key_id, server_key_id):
        self._client_key_id = client_key_id
        self._server_key_id = server_key_id

    def __call__(self, r):
        key_obj = HTTPSignatureKey.objects.get(key_id=self._server_key_id)
        # Use the `clientId` parameter to distinguish sent and received nonces.
        client_id = force_text(int_from_bytes(hashlib.sha256(force_bytes(self._client_key_id)).digest()[:16], 'big'))
        # Generate a valid `nonce`-`date` pair.
        created = False
        while not created:
            nonce = force_text(int_from_bytes(os.urandom(4), 'big'))
            date = timezone.now().replace(microsecond=0)
            nonce_obj, created = HTTPSignatureNonce.objects.get_or_create(
                key=key_obj,
                client_id=client_id,
                nonce=nonce,
                date__gte=date - 2 * HTTPSignatureNonce.MAX_CLOCK_SKEW,
                defaults={'date': date},
            )
        # Generate the `host` header.
        r.headers['Host'] = urlparse(r.url).netloc
        # Generate the `date` header.
        r.headers['Date'] = http_date(calendar.timegm(date.utctimetuple()))
        # Generate the `digest` header.
        if r.body:
            r.headers['Digest'] = 'SHA-256=' + force_text(base64.b64encode(hashlib.sha256(r.body).digest()))
        # Generate the `headers` parameter.
        headers = list(self.generic_headers)
        if r.body:
            headers.extend(self.body_headers)
        # Generate the `signature` parameter.
        string_to_sign = []
        for header in headers:
            if header == '(request-target)':
                value = '%s %s' % (r.method.lower(), r.path_url)
            elif header == '(request-nonce)':
                value = '%s %s' % (client_id, nonce)
            else:
                value = r.headers[header]
            string_to_sign.append('%s: %s' % (header, value))
        string_to_sign = '\n'.join(string_to_sign)
        h = hmac.new(force_bytes(key_obj.key), force_bytes(string_to_sign), digestmod=hashlib.sha256)
        signature = base64.b64encode(h.digest())
        # Build the `authorization` header.
        r.headers['Authorization'] = 'Signature %s' % ','.join('%s="%s"' % (k, v) for k, v in [
            ('keyId', self._client_key_id),
            ('algorithm', 'hmac-sha256'),
            ('headers', ' '.join(headers)),
            ('clientId', client_id),
            ('nonce', nonce),
            ('signature', signature),
        ])
        return r


class APISession(requests.Session):
    client_username = None
    server_username = None

    def __init__(self, *args, **kwargs):
        super(APISession, self).__init__(*args, **kwargs)
        self.auth = HTTPSignatureAuth(self.client_username, self.server_username)
        self.verify = getattr(settings, 'DEMOS_VOTING_API_VERIFY', True)

    def request(self, method, url, *args, **kwargs):
        assert not url.startswith('/')
        base_urls = getattr(settings, 'DEMOS_VOTING_INTERNAL_URLS', None) or settings.DEMOS_VOTING_URLS
        url = urljoin(base_urls[self.server_username], 'api/%s' % url)
        return super(APISession, self).request(method, url, *args, **kwargs)
