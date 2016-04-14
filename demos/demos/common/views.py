# File: views.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

logger = logging.getLogger(__name__)


class TestPrivateApiView(View):
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(TestPrivateApiView, self).dispatch(*args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        return HttpResponse(status=200)
    
    def post(self, request, *args, **kwargs):
        return HttpResponse(status=200)

