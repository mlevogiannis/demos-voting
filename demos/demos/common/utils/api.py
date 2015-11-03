# File: api.py

from __future__ import division

import logging
import requests

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

from six import string_types

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.middleware import csrf
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm


class Session:
    _log = logging.getLogger(__name__ + '.Session')
    
    def __init__(self, server, app_config):
        
        self.s = requests.Session()
        
        self.username = app_config.label
        self.password = app_config.get_model('RemoteUser').\
            objects.get(username=server).password
        
        self.url = urljoin(settings.DEMOS_API_URL[server], 'api/')
        self.verify = getattr(settings, 'DEMOS_API_VERIFY', True)
        
        self.login()
    
    def __del__(self):
        try:
            self.logout()
        except Exception:
            self._log.warning("Could not logout:", exc_info=True)
    
    def login(self):
        
        url = urljoin(self.url, 'auth/login/')
        r = self.s.get(url, verify=self.verify)
        r.raise_for_status()
        
        payload = {
            'username': self.username,
            'password': self.password,
            'csrfmiddlewaretoken': self.s.cookies.get('csrftoken', False),
        }
        
        r = self.s.post(url, data=payload, verify=self.verify)
        r.raise_for_status()
    
    def logout(self):
        
        url = urljoin(self.url, 'auth/logout/')
        r = self.s.get(url, verify=self.verify)
        r.raise_for_status()
    
    def post(self, path, data={}, files=None, _retry_login=True):
        
        try:
            url = urljoin(self.url, path)
            
            r = self.s.get(url, verify=self.verify)
            r.raise_for_status()
            
            data['csrfmiddlewaretoken'] = self.s.cookies.get('csrftoken', False)
            
            r = self.s.post(url, data=data, files=files, verify=self.verify)
            r.raise_for_status()
            
            return r
        
        except requests.exceptions.HTTPError as e:
            if r.status_code == requests.codes.unauthorized and _retry_login:
                self.login()
                self.post(path, data, file, False)
            else:
                self._log.warning("Cannot send request: %s", e)
                raise


def login(request):
    """API login view"""
    
    if request.method == 'POST':
    
        form = AuthenticationForm(request, data=request.POST)
        
        if form.is_valid():
            auth_login(request, form.get_user())
            return HttpResponse()
        
        return HttpResponse(status=401)
    
    csrf.get_token(request)
    return HttpResponse()


def logout(request):
    """API logout view"""
    
    auth_logout(request)
    return HttpResponse()


def user_required(username):
    """
    Decorator for views that checks that a specific user or at least one of the
    users in a list is logged in. On error, returns Unauthorized or Forbidden.
    """
    
    # Ensure that username is always an iterable
    if isinstance(username, string_types):
        username = [username]
    
    def decorator(view_func):
        
        def _wrapped_view(request, *args, **kwargs):
            
            # If the user is not logged in, return Unauthorized (401)
            if not request.user.is_authenticated():
                return HttpResponse(status=401)
            
            # If the user is not in the list, return Forbidden (403)
            if not request.user.username in username:
                return HttpResponseForbidden()
            
            return view_func(request, *args, **kwargs)
            
        return _wrapped_view
        
    return decorator

