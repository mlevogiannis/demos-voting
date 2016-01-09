# File: decorators.py

from __future__ import absolute_import, division, print_function, unicode_literals

from functools import wraps
from django.db.models import Manager


def related(*related_fields):
    def decorator(func):
        
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            
            if not isinstance(self, Manager):
                raise TypeError("'%s' must be a method of a '%s' instance" % (func.__name__, Manager.__name__))
            
            related_models = tuple(getattr(self.model, f).field.related_model for f in related_fields)
            
            if not (hasattr(self, 'instance') and isinstance(self.instance, related_models)):
                raise AttributeError("'%s' is only available to related managers of: '%s'" %
                    (func.__name__, "' '".join(related_fields)))
            
            return func(self, *args, **kwargs)
            
        return wrapper
    return decorator

