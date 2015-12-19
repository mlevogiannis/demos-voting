# File: views.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from django import http
from django.conf import settings
from django.middleware import csrf
from django.views.generic import View

from .session import ApiSession
from demos.common.utils.setup import insert_into_db

logger = logging.getLogger(__name__)


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

