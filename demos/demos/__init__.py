# File: __init__.py

from . import settings

if set(settings.DEMOS_APPS) & set(['ea', 'bds', 'abb']):
    from .celery import app as celery_app

