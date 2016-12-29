# File: tasks.py

from __future__ import absolute_import, division, print_function, unicode_literals

from celery.signals import before_task_publish, task_postrun

from demos_voting.apps.ea.models import Election, Task


@before_task_publish.connect
def create_task(**kwargs):
    election_id = kwargs['body']['kwargs'].get('election_id', kwargs['body']['args'][0])
    task_name = kwargs['body']['task']
    task_id = kwargs['body']['id']
    election = Election.objects.only('pk').get(id=election_id)
    Task.objects.create(election_id=election.pk, name=task_name, id=task_id)

@task_postrun.connect
def delete_task(**kwargs):
    election_id = kwargs['kwargs'].get('election_id', kwargs['args'][0])
    task_name = kwargs['task'].name
    task_id = kwargs['task_id']
    Task.objects.filter(election__id=election_id, name=task_name, id=task_id).delete()
