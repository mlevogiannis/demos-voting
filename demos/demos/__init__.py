# File: __init__.py

from .settings import base

if set(base.DEMOS_APPS).intersection(['ea', 'bds', 'abb']):
	from .settings.celeryapp import app as celery_app

#eof
