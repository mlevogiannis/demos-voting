# File: decorators.py

from __future__ import absolute_import, division, print_function, unicode_literals

import functools


def related_attr(*fields):
    def decorator(func):
        
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            
            related_models = tuple(self.model._meta.get_field(f).related_model for f in fields)
            
            if not (hasattr(self, 'instance') and isinstance(self.instance, related_models)):
                raise AttributeError("%s is only accessible via reverse relations: %s"
                                     % (func.__name__, "' '".join(fields)))
            
            return func(self, *args, **kwargs)
            
        return wrapper
    return decorator

