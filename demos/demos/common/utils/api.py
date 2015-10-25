# File: api.py

import requests

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.middleware import csrf

from demos.settings import DEMOS_API_URL

import logging
from six import string_types

class Session:
    _log = logging.getLogger('demos.remoteSession')
    
    def __init__(self, server, app_config):
        
        self.s = requests.Session()
        
        self.username = app_config.label
        self.password = app_config.get_model('RemoteUser').\
            objects.get(username=server).password
        self.url = urljoin(DEMOS_API_URL[server], 'api/')
        
        self.login()
    
    def __del__(self):
        try:
            self.logout()
        except Exception:
            self._log.warning("Could not logout:", exc_info=True)
    
    def login(self):
        
        url = urljoin(self.url, 'auth/login/')
        r = self.s.get(url) # won't authenticate, only get the CSRF token
        r.raise_for_status()
        
        payload = {
            'username': self.username,
            'password': self.password,
            'csrfmiddlewaretoken': self.s.cookies['csrftoken'],
        }
        
        r = self.s.post(url, data=payload, verify=True)
        r.raise_for_status()
    
    def logout(self):
        
        url = urljoin(self.url, 'auth/logout/')
        r = self.s.get(url)
        r.raise_for_status()
    
    def post(self, path, data={}, files=None, _retry_login=True):
        
        try:
            url = urljoin(self.url, path)
            
            r = self.s.get(url)
            r.raise_for_status()
            
            data['csrfmiddlewaretoken'] = self.s.cookies['csrftoken']
            
            r = self.s.post(url, data=data, files=files, verify=True)
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

