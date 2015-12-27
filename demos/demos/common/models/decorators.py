# File: decorators.py

from __future__ import absolute_import, division, print_function, unicode_literals

import functools


def rel_cache(rel_field_name):
    def decorator(func):
        
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            
            field = getattr(self.model, rel_field_name).field
            instance = getattr(self, 'instance', None)
            
            if isinstance(instance, field.related_model):
                attr = '_%s_%s' % (field.related_query_name(), func.__name__)
                if not hasattr(instance, attr):
                    setattr(instance, attr, func(self, *args, **kwargs))
                return getattr(instance, attr)
            
            return func(self, *args, **kwargs)
            
        return wrapper
    return decorator

