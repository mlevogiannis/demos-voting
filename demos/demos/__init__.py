# File: __init__.py

from .settings import demos

if demos.DEMOS_MAIN in ('ea', 'bds', 'abb'):
	from .settings.celery import app as celery_app
