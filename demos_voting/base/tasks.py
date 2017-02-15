# File: tasks.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import apps
from django.conf import settings

from celery.signals import before_task_publish, task_postrun


@before_task_publish.connect
def create_task(**kwargs):
    task_name = kwargs['body']['task']

    app_label = task_name.split('.', 1)[0]
    if app_label not in settings.DEMOS_VOTING_APPS:
        return

    app_config = apps.get_app_config(app_label)

    election_id = kwargs['body']['kwargs']['election_id']
    election_model = app_config.get_model('Election')
    election = election_model.objects.only('pk').get(id=election_id)

    task_id = kwargs['body']['id']
    task_model = app_config.get_model('Task')
    task_model.objects.create(election=election, name=task_name, id=task_id)


@task_postrun.connect
def delete_task(**kwargs):
    task_name = kwargs['task'].name

    app_label = task_name.split('.', 1)[0]
    if app_label not in settings.DEMOS_VOTING_APPS:
        return

    app_config = apps.get_app_config(app_label)

    task_id = kwargs['task_id']
    task_model = app_config.get_model('Task')
    task_model.objects.filter(id=task_id).delete()

