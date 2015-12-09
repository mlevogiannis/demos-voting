# File: session.py

from __future__ import absolute_import, division, unicode_literals

import json
import logging
import requests

from django.conf import settings
from django.utils.six.moves.urllib.parse import urljoin

from demos.common.utils.json import CustomJSONEncoder

logger = logging.getLogger(__name__)


class ApiSession(object):
    
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

