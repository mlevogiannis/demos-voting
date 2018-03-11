from __future__ import absolute_import, division, print_function, unicode_literals

from celery import shared_task
from celery.schedules import crontab

from django.utils import timezone

from demos_voting.base.models import HTTPSignatureNonce
from demos_voting.celery import app as celery_app


@shared_task
def clean_up_expired_http_signature_nonces():
    HTTPSignatureNonce.objects.filter(date__lt=timezone.now() - 2 * HTTPSignatureNonce.MAX_CLOCK_SKEW).delete()


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Executes daily at midnight.
    sender.add_periodic_task(crontab(minute=0, hour=0), clean_up_expired_http_signature_nonces.s())
