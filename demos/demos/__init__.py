# File: __init__.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings

if set(settings.DEMOS_APPS) & set(['ea', 'bds', 'abb']):
    
    import json
    
    from functools import partial
    from kombu.serialization import register
    from django.core.serializers.json import DjangoJSONEncoder
    
    register('custom-json', partial(json.dumps, cls=DjangoJSONEncoder), json.loads, 'application/x-custom-json')
    
    from .celery import app as celery_app

