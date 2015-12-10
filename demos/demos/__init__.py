# File: __init__.py

from django.conf import settings

if set(settings.DEMOS_APPS) & set(['ea', 'bds', 'abb']):
    
    import json
    
    from functools import partial
    from kombu.serialization import register
    from demos.common.utils.json import CustomJSONEncoder
    
    register('custom-json', partial(json.dumps, cls=CustomJSONEncoder), json.loads, 'application/x-custom-json')
    
    from .celery import app as celery_app

