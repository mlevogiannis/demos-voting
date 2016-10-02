# File: views.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

logger = logging.getLogger(__name__)


class PrivateApiView(View):
    
    @classmethod
    def as_view(cls, **initkwargs):
        
        # Backport (Django 1.9): Keep reference to view class.
        # https://code.djangoproject.com/ticket/24055
        # https://github.com/django/django/commit/a420f83e7d2e446ca01ef7c13d30c2ef3e975e5c
        
        view = super(PrivateApiView, cls).as_view(**initkwargs)
        assert not (hasattr(view, 'view_class') or hasattr(view, 'view_initkwargs'))
        
        view.view_class = cls
        view.view_initkwargs = initkwargs
        
        return view
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(PrivateApiView, self).dispatch(*args, **kwargs)


class TestPrivateApiView(PrivateApiView):
    
    def get(self, request, *args, **kwargs):
        return HttpResponse(status=200)
    
    def post(self, request, *args, **kwargs):
        return HttpResponse(status=200)

