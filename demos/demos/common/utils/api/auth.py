# File: auth.py

from __future__ import absolute_import, division, unicode_literals

import logging

from django import http
from django.db import models
from django.conf import settings
from django.utils import six
from django.middleware import csrf
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.utils.encoding import python_2_unicode_compatible
from django.contrib.auth.forms import AuthenticationForm

logger = logging.getLogger(__name__)


def login(request):
    """API login view"""
    
    if request.method == 'POST':
    
        form = AuthenticationForm(request, data=request.POST)
        
        if form.is_valid():
            auth_login(request, form.get_user())
            return http.HttpResponse()
        
        return http.HttpResponse(status=401)
    
    csrf.get_token(request)
    return http.HttpResponse()


def logout(request):
    """API logout view"""
    
    auth_logout(request)
    return http.HttpResponse()


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
                return http.HttpResponse(status=401)
            
            # If the user is not in the list, return Forbidden (403)
            if not request.user.username in username:
                return http.HttpResponseForbidden()
            
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

