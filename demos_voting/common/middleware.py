# File: middleware.py

from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib
import hmac
import logging
import re
import time

from django.apps import apps
from django.conf import settings
from django.contrib import auth
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.utils.crypto import constant_time_compare
from django.utils.encoding import force_bytes, force_text

from demos_voting.common.views import PrivateApiView
from demos_voting.common.utils.private_api import PRIVATE_API_AUTH_PARAMS, PRIVATE_API_AUTH_SCHEME

logger = logging.getLogger(__name__)


class PrivateApiMiddleware(object):
    
    def __init__(self):
        
        self.credentials_re = re.compile(PRIVATE_API_AUTH_SCHEME + ' ' + PRIVATE_API_AUTH_PARAMS % {
            'app_label': r'(?P<app_label>ea|bds|abb|vbb)',
            'timestamp': r'(?P<timestamp>[0-9]+)',
            'nonce': r'(?P<nonce>[0-9a-f]{32})',
            'digest': r'(?P<digest>[0-9a-f]{128})',
        })
        
        self.nonce_timeout = getattr(settings, 'DEMOS_VOTING_PRIVATE_API_NONCE_TIMEOUT', 300)
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        
        if not issubclass(getattr(view_func, 'view_class', None), PrivateApiView):
            return None
        
        if hasattr(request, 'user') and request.user.is_authenticated():
            auth.logout(request)
        
        try:
            user = self._authenticate(request)
        except PermissionDenied:
            response = HttpResponse(status=401)
            response['WWW-Authenticate'] = PRIVATE_API_AUTH_SCHEME
            return response
        
        request.user = user
    
    def process_exception(self, request, exception):
        
        if not issubclass(getattr(request.resolver_match.func, 'view_class', None), PrivateApiView):
            return None
        
        return HttpResponse(status=422)
    
    @transaction.atomic
    def _authenticate(self, request):
        
        # Get timestamp upper/lower bounds.
        
        now_timestamp = int(time.time())
        
        min_timestamp = now_timestamp - self.nonce_timeout
        max_timestamp = now_timestamp + self.nonce_timeout
        
        # Read the HTTP Authorization header.
        
        m = self.credentials_re.match(request.META.get('HTTP_AUTHORIZATION', ''))
        if m is None:
            raise PermissionDenied
        
        credentials = m.groupdict()
        
        # Validate timestamp.
        
        timestamp = int(credentials['timestamp'])
        
        if timestamp < min_timestamp or timestamp > max_timestamp:
            raise PermissionDenied
        
        # Get remote app's user and nonces.
        
        local_app_label = request.resolver_match.app_name
        remote_app_label = force_text(credentials['app_label'])
        
        app_config = apps.get_app_config(local_app_label)
        
        PrivateApiUser = app_config.get_model('PrivateApiUser')
        PrivateApiNonce = app_config.get_model('PrivateApiNonce')
        
        try:
            user = PrivateApiUser.objects.select_for_update().get(app_label=remote_app_label)
        except PrivateApiUser.DoesNotExist:
            raise PermissionDenied
        
        nonces = user.nonces.filter(type=PrivateApiNonce.TYPE_REMOTE)
        
        # Remove expired remote nonces.
        
        nonces.filter(timestamp__lt=min_timestamp).delete()
        
        # Validate nonce.
        
        nonce = force_text(credentials['nonce'])
        
        if nonces.filter(nonce=nonce, timestamp=timestamp).exists():
            raise PermissionDenied
        
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
        
        digest1 = force_text(credentials['digest'])
        digest2 = force_text(h.hexdigest())
        
        if not constant_time_compare(digest1, digest2):
            raise PermissionDenied
        
        # Update remote nonces.
        
        user.nonces.create(nonce=nonce, timestamp=timestamp, type=PrivateApiNonce.TYPE_REMOTE)
        
        return user

