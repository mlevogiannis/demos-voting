from __future__ import absolute_import, division, print_function, unicode_literals

import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demos_voting.settings')

app = Celery('demos_voting')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
