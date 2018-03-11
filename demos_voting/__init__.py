from __future__ import absolute_import, division, print_function, unicode_literals

from .celery import app as celery_app

__all__ = ['celery_app']
