# File: tally.py

from celery import shared_task


@shared_task(ignore_result=True)
def election_setup(election, election_obj, language):
    pass
