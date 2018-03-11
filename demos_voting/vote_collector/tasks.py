from __future__ import absolute_import, division, print_function, unicode_literals

import multiprocessing

from celery import shared_task, chord
from celery.signals import task_failure

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from demos_voting.base.utils import get_range_in_chunks
from demos_voting.vote_collector.models import Ballot, Election
from demos_voting.vote_collector.serializers import BulletinBoardBallotSerializer, ElectionSerializer
from demos_voting.vote_collector.utils.api import BulletinBoardAPISession

TASK_CONCURRENCY = getattr(settings, 'DEMOS_VOTING_TASK_CONCURRENCY', None) or multiprocessing.cpu_count()


# Voting phase tasks ##########################################################

@shared_task(ignore_result=True)
def prepare_voting_phase(election_pk):
    """
    Prepare the election's voting phase.
    """
    with transaction.atomic():
        election = Election.objects.select_for_update().get(pk=election_pk)
        if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
            return
        assert election.state == election.STATE_VOTING
        election.voting_started_at = timezone.now()
        election.save()
    # Schedule publishing of the ballots that have been cast.
    prepare_publish_cast_ballots.apply_async(args=(election.pk,), eta=election.voting_ends_at)


@shared_task(ignore_result=True)
def extend_voting_period(election_pk):
    election = Election.objects.get(pk=election_pk)
    if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
        return
    assert election.state == election.STATE_VOTING
    # Notify the Bulletin Board that the voting phase has been extended.
    with BulletinBoardAPISession() as s:
        serializer = ElectionSerializer(instance=election, fields=['voting_ends_at'])
        r = s.patch('elections/%s/' % election.slug, json=serializer.data)
        r.raise_for_status()


@shared_task(bind=True, ignore_result=True, max_retries=None)
def prepare_publish_cast_ballots(self, election_pk):
    """
    Send the ballots that have been cast to the Bulletin Board.
    """
    with transaction.atomic():
        election = Election.objects.select_for_update().get(pk=election_pk)
        if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
            return
        assert election.state == election.STATE_VOTING
        if timezone.now() < election.voting_ends_at:
            # The voting end time was extended, retry later.
            raise self.retry(eta=election.voting_ends_at)
    # Lock all the ballot objects. Do this to properly handle the case where a
    # ballot might be submitted to (and locked by) `VotingBoothView.post()`
    # before the voting period has ended but validation and saving might finish
    # after the voting period has ended. This ballot should still be accepted
    # and thus the code below should should run only after that ballot has been
    # saved (and its lock has been released).
    with transaction.atomic():
        # Do the locking in a subquery to avoid fetching any results.
        Ballot.objects.filter(pk__in=election.ballots.select_for_update()).exists()
    # Start the publish cast ballots tasks.
    ballot_count = election.ballots.filter(parts__is_cast=True).distinct().count()
    publish_cast_ballots_tasks = [
        publish_cast_ballots.si(election_pk, range_start, range_stop)
        for range_start, range_stop in get_range_in_chunks(ballot_count, TASK_CONCURRENCY)
    ]
    finalize_voting_phase_task = finalize_voting_phase.si(election_pk=election_pk)
    chord(publish_cast_ballots_tasks, finalize_voting_phase_task).delay()


@shared_task
def publish_cast_ballots(election_pk, range_start, range_stop):
    """
    Select the ballots that have been cast from the specified range and send
    them to the Bulletin Board.
    """
    election = Election.objects.get(pk=election_pk)
    if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
        return
    assert election.state == election.STATE_VOTING
    # Send the cast ballot objects to the Bulletin Board.
    ballots = election.ballots.filter(parts__is_cast=True).distinct()
    with BulletinBoardAPISession() as s:
        for ballot in ballots[range_start: range_stop].iterator():
            serializer = BulletinBoardBallotSerializer(ballot, context={'election': election})
            r = s.patch('elections/%s/ballots/%d/' % (election.slug, ballot.serial_number), json=serializer.data)
            r.raise_for_status()


@shared_task(ignore_result=True)
def finalize_voting_phase(election_pk):
    """
    Finalize the election's voting phase.
    """
    with transaction.atomic():
        election = Election.objects.select_for_update().get(pk=election_pk)
        if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
            return
        assert election.state == election.STATE_VOTING
        election.state = election.STATE_COMPLETED
        election.voting_ended_at = timezone.now()
        election.save()


# Voting phase task failure handlers ##########################################

@task_failure.connect(sender=prepare_voting_phase)
def prepare_voting_phase_task_failure(**kwargs):
    voting_task_failure_handler(**kwargs)


@task_failure.connect(sender=extend_voting_period)
def extend_voting_period_task_failure(**kwargs):
    voting_task_failure_handler(**kwargs)


@task_failure.connect(sender=prepare_publish_cast_ballots)
def prepare_publish_cast_ballots_task_failure(**kwargs):
    voting_task_failure_handler(**kwargs)


@task_failure.connect(sender=publish_cast_ballots)
def publish_cast_ballots_task_failure(**kwargs):
    voting_task_failure_handler(**kwargs)


@task_failure.connect(sender=finalize_voting_phase)
def finalize_voting_phase_task_failure(**kwargs):
    voting_task_failure_handler(**kwargs)


def voting_task_failure_handler(**kwargs):
    election_pk = kwargs['kwargs'].get('election_pk', next(iter(kwargs['args']), None))
    with transaction.atomic():
        election = Election.objects.select_for_update().get(pk=election_pk)
        if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
            return
        assert election.state == election.STATE_VOTING
        election.state = election.STATE_FAILED
        election.voting_ended_at = timezone.now()
        election.save()
