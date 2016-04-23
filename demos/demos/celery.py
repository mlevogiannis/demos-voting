# File: celery.py

from __future__ import absolute_import, division, print_function, unicode_literals

import functools
import json
import os

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder

from celery import Celery
from kombu.serialization import register


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demos.settings')

app = Celery('demos')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


register(
    name='json',
    encoder=functools.partial(json.dumps, cls=DjangoJSONEncoder),
    decoder=json.loads,
    content_type='application/json',
    content_encoding='utf-8',
)

