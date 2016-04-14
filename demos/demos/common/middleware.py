# File: middleware.py

from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib
import hmac
import logging
import re
import time

from django.apps import apps
from django.db import transaction
from django.http import HttpResponse
from django.utils.crypto import constant_time_compare
from django.utils.encoding import force_bytes, force_text

from demos.common.utils.private_api import PRIVATE_API_AUTHORIZATION_HEADER

logger = logging.getLogger(__name__)


class PrivateApiMiddleware(object):
    
    NONCE_TIMEOUT = 120
    
    def __init__(self):
        
        self.authorization_header_re = re.compile(PRIVATE_API_AUTHORIZATION_HEADER % {
            'app_label': r'(?P<app_label>ea|bds|abb|vbb)',
            'timestamp': r'(?P<timestamp>[0-9]+)',
            'nonce': r'(?P<nonce>[0-9a-f]{16})',
            'digest': r'(?P<digest>[0-9a-f]{128})',
        })
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        
        app_name = request.resolver_match.app_name
        namespaces = request.resolver_match.namespaces
        
        if len(namespaces) >= 2 and namespaces[0] == '%s-api' % app_name and namespaces[1] == 'private':
            return self._authenticate(request)
    
    @transaction.atomic
    def _authenticate(self, request):
        
        # Get timestamp upper/lower bounds.
        
        now_timestamp = int(time.time())
        
        min_timestamp = now_timestamp - self.NONCE_TIMEOUT
        max_timestamp = now_timestamp + self.NONCE_TIMEOUT
        
        # Read the HTTP Authorization header.
        
        m = self.authorization_header_re.match(request.META.get('HTTP_AUTHORIZATION', ''))
        
        if m is None:
            return HttpResponse(status=400)
        
        authorization_header = m.groupdict()
        
        # Validate timestamp.
        
        timestamp = int(authorization_header['timestamp'])
        
        if timestamp < min_timestamp or timestamp > max_timestamp:
            return HttpResponse(status=401)
        
        # Get remote app's user object.
        
        local_app_label = request.resolver_match.app_name
        remote_app_label = force_text(authorization_header['app_label'])
        
        PrivateApiUser = apps.get_app_config(local_app_label).get_model('PrivateApiUser')
        
        try:
            user = PrivateApiUser.objects.select_for_update().get(app_label=remote_app_label)
        except PrivateApiUser.DoesNotExist:
            return HttpResponse(status=401)
        
        # Remove expired nonces.
        
        user.received_nonces = [(n, t) for (n, t) in user.received_nonces if t >= min_timestamp]
        
        # Validate nonce.
        
        nonce = force_text(authorization_header['nonce'])
        
        if (nonce, timestamp) in user.received_nonces:
            return HttpResponse(status=401)
        
        # Validate digest.
        
        elements = [
            remote_app_label,
            timestamp,
            nonce,
            request.method,
            request.path,
            request.META.get('QUERY_STRING', ''),
            request.body,
        ]
        
        h = hmac.new(force_bytes(user.preshared_key), digestmod=hashlib.sha512)
        for e in elements:
            h.update(force_bytes(e))
        
        digest1 = force_text(authorization_header['digest'])
        digest2 = force_text(h.hexdigest())
        
        if not constant_time_compare(digest1, digest2):
            return HttpResponse(status=401)
        
        # Update the list of received nonces.
        
        user.received_nonces.append((nonce, timestamp))
        user.save(update_fields=['received_nonces'])
        
        # Authenticate the user.
        
        request.user = user

