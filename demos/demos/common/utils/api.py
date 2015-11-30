# File: api.py

from __future__ import absolute_import, division, unicode_literals

import json
import logging
import requests

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

from django import http
from django.db import models, transaction
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import six
from django.middleware import csrf
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.views.generic import View
from django.utils.encoding import python_2_unicode_compatible
from django.utils.decorators import method_decorator
from django.contrib.auth.forms import AuthenticationForm

from demos.common.utils.json import CustomJSONEncoder
from demos.common.utils.setup import insert_into_db

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------

class ApiSession:
    
    _csrftoken = settings.CSRF_COOKIE_NAME
    _csrfmiddlewaretoken = 'csrfmiddlewaretoken'
    
    _verify = getattr(settings, 'DEMOS_API_VERIFY', True)
    
    def __init__(self, remote_app, app_config, logger=logger):
        
        self.s = requests.Session()
        
        self.logger = logger
        self.url = settings.DEMOS_API_URL[remote_app]
        
        self.username = app_config.label
        self.password = app_config.get_model('RemoteUser').\
            objects.get(username=remote_app).password
        
        self.login()
    
    def __del__(self):
        
        try:
            self.logout()
        except Exception:
            self.logger.warning("Could not logout:", exc_info=True)
    
    def login(self):
        
        url = urljoin(self.url, 'api/auth/login/')
        r = self.s.get(url, verify=self._verify)
        r.raise_for_status()
        
        data = {
            'username': self.username,
            'password': self.password,
            
            self._csrfmiddlewaretoken: self.s.cookies.get(self._csrftoken),
        }
        
        r = self.s.post(url, data=data, verify=self._verify)
        r.raise_for_status()
    
    def logout(self):
        
        url = urljoin(self.url, 'api/auth/logout/')
        r = self.s.get(url, verify=self._verify)
        r.raise_for_status()
    
    def _post(self, path, data={}, files=None, _retry_login=True):
        
        try:
            url = urljoin(self.url, path)
            
            r = self.s.get(url, verify=self._verify)
            r.raise_for_status()
            
            assert self._csrfmiddlewaretoken not in data
            data[self._csrfmiddlewaretoken]=self.s.cookies.get(self._csrftoken)
            
            r = self.s.post(url, data=data, files=files, verify=self._verify)
            r.raise_for_status()
            
            return r
        
        except requests.exceptions.HTTPError as e:
            
            if r.status_code == requests.codes.unauthorized and _retry_login:
                self.login()
                self._post(path, data, files, _retry_login=False)
            else:
                raise
    
    def post(self, path, data={}, files=None, **kwargs):
        
        if kwargs.get('json', False):
            
            data = data.copy()
            encoder = kwargs.get('encoder', CustomJSONEncoder)
            
            for key, value in data.items():
                data[key] = json.dumps(value, cls=encoder, separators=(',',':'))
        
        return self._post(path, data, files, _retry_login=True)
    
    @classmethod
    def load_json_request(cls, request):
        
        data = {}
        
        request = request.copy()
        
        if cls._csrfmiddlewaretoken in request:
            del request[cls._csrfmiddlewaretoken]
        
        for key, value in request.items():
            data[key] = json.loads(value)
        
        return data

# ------------------------------------------------------------------------------

class _ApiBaseView(View):
    
    def __init__(self, *args, **kwargs):
        
        self.app_config = kwargs.pop('app_config')
        self.logger = kwargs.pop('logger', logger)
        
        super(_ApiBaseView, self).__init__(*args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        
        csrf.get_token(request)
        return http.HttpResponse()
    

class ApiSetupView(_ApiBaseView):
    
    def post(self, request, data=None, *args, **kwargs):
        
        try:
            if data is None:
                data = ApiSession.load_json_request(request.POST)
            
            insert_into_db(data, self.app_config)
            
        except Exception:
            self.logger.exception('SetupView: API error')
            return http.HttpResponse(status=422)
        
        return http.HttpResponse()


class ApiUpdateView(_ApiBaseView):
    
    def post(self, request, data=None, *args, **kwargs):
        
        try:
            if data is None:
                data = ApiSession.load_json_request(request.POST)
            
            fields = data['fields']
            natural_key = data['natural_key']
            model = self.app_config.get_model(data['model'])
            
            obj = model.objects.get_by_natural_key(**natural_key)
            
            for name, value in fields.items():
                setattr(obj, name, value)
            
            obj.save(update_fields=list(fields.keys()))
            
        except Exception:
            self.logger.exception('UpdateView: API error')
            return http.HttpResponse(status=422)
        
        return http.HttpResponse()

# ------------------------------------------------------------------------------

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
    if isinstance(username, six.string_types):
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


@python_2_unicode_compatible
class RemoteUserBase(models.Model):
    
    username = models.CharField(max_length=128, unique=True)
    password = models.CharField(max_length=128)
    
    # Other model methods and meta options
    
    def __str__(self):
        return "%s - %s" % (self.username, self.password)
    
    class Meta:
        abstract = True
    
    class RemoteUserManager(models.Manager):
        def get_by_natural_key(self, username):
            return self.get(username=username)
    
    objects = RemoteUserManager()
    
    def natural_key(self):
        return (self.username,)

