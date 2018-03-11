from __future__ import absolute_import, division, print_function, unicode_literals

import multiprocessing

from celery import chord, shared_task
from celery.signals import task_failure

from django.conf import settings
from django.core import mail
from django.db import transaction
from django.db.models import prefetch_related_objects
from django.utils import timezone

from demos_voting.base.utils import get_range_in_chunks
from demos_voting.bulletin_board.models import Election

TASK_CONCURRENCY = getattr(settings, 'DEMOS_VOTING_TASK_CONCURRENCY', None) or multiprocessing.cpu_count()


# Tally phase tasks ###########################################################

@shared_task(ignore_result=True)
def prepare_tally_phase(election_pk):
    """
    Prepare the election's tally phase.
    """
    with transaction.atomic():
        election = Election.objects.select_for_update().prefetch_related('questions__options').get(pk=election_pk)
        if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
            return
        assert election.state == election.STATE_TALLY
        election.tally_started_at = timezone.now()
        election.save()
    # Generate the voters' coins.
    election.generate_coins()
    election.save(update_fields=['coins'])
    # Generate the tally commitment.
    for question in election.questions.all():
        question.generate_tally_commitment()
        question.save(update_fields=['tally_commitment'])
    # Notify the trustees to participate.
    with mail.get_connection() as connection:
        for trustee in election.trustees.iterator():
            trustee.send_tally_notification_mail(connection=connection)


@shared_task(ignore_result=True)
def generate_election_results(election_pk):
    """
    Combine the partial tally decommitments and extract the election results.
    """
    election = Election.objects.prefetch_related('questions__options').get(pk=election_pk)
    if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
        return
    assert election.state == election.STATE_TALLY
    # Generate the tally decommitment and the vote counts.
    for question in election.questions.all():
        question.generate_tally_decommitment()
        question.save(update_fields=['tally_decommitment'])
        for option in question.options.all():
            option.generate_vote_count()
            option.save(update_fields=['vote_count'])
    # Start the tasks to generate the ballot audit data.
    ballot_count = election.ballots.filter(parts__is_cast=True).distinct().count()
    generate_ballot_audit_data_tasks = [
        generate_ballot_audit_data.si(election_pk, range_start, range_stop)
        for range_start, range_stop in get_range_in_chunks(ballot_count, TASK_CONCURRENCY)
    ]
    finalize_tally_phase_task = finalize_tally_phase.si(election_pk=election_pk)
    chord(generate_ballot_audit_data_tasks, finalize_tally_phase_task).delay()


@shared_task
def generate_ballot_audit_data(election_pk, range_start, range_stop):
    """
    Combine the partial decommitments of the ballot parts that have not been
    cast or the ZK2 of the ballot parts that have been cast.
    """
    election = Election.objects.get(pk=election_pk)
    if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
        return
    assert election.state == election.STATE_TALLY
    # Generate the specified ballots' audit data.
    ballots = election.ballots.filter(parts__is_cast=True).distinct()
    ballots = ballots[range_start: range_stop]
    for ballot in ballots.iterator():
        prefetch_related_objects([ballot], 'parts__questions__options')
        for ballot_part in ballot.parts.all():
            for ballot_question in ballot_part.questions.all():
                ballot_question.generate_zk2()
                ballot_question.save(update_fields=['zk2'])
                for ballot_option in ballot_question.options.all():
                    ballot_option.generate_zk2()
                    ballot_option.generate_decommitment()
                    ballot_option.restore_election_option()
                    ballot_option.save(update_fields=['zk2', 'decommitment', 'election_option'])


@shared_task(ignore_result=True)
def finalize_tally_phase(election_pk):
    """
    Finalize the election's tally phase.
    """
    with transaction.atomic():
        election = Election.objects.select_for_update().get(pk=election_pk)
        if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
            return
        assert election.state == election.STATE_TALLY
        election.state = election.STATE_COMPLETED
        election.tally_ended_at = timezone.now()
        election.save()
    # Notify the voters that the results have been released.
    if election.voters.exists():
        with mail.get_connection(fail_silently=True) as connection:
            for voter in election.voters.iterator():
                voter.send_election_results_mail(connection=connection)


# Tally phase task failure handlers ###########################################

@task_failure.connect(sender=prepare_tally_phase)
def prepare_tally_task_failure(**kwargs):
    tally_task_failure_handler(**kwargs)


@task_failure.connect(sender=generate_election_results)
def generate_election_results_task_failure(**kwargs):
    tally_task_failure_handler(**kwargs)


@task_failure.connect(sender=generate_ballot_audit_data)
def generate_ballot_audit_data_task_failure(**kwargs):
    tally_task_failure_handler(**kwargs)


@task_failure.connect(sender=finalize_tally_phase)
def finalize_tally_task_failure(**kwargs):
    tally_task_failure_handler(**kwargs)


def tally_task_failure_handler(**kwargs):
    election_pk = kwargs['kwargs'].get('election_pk', next(iter(kwargs['args']), None))
    with transaction.atomic():
        election = Election.objects.select_for_update().get(pk=election_pk)
        if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
            return
        assert election.state == election.STATE_TALLY
        election.state = election.STATE_FAILED
        election.tally_ended_at = timezone.now()
        election.save()
