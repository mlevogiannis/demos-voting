from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import multiprocessing

from celery import chord, shared_task
from celery.signals import task_failure

from django.conf import settings
from django.core import mail
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import prefetch_related_objects
from django.utils import timezone

from six.moves import zip

from demos_voting.ballot_distributor.models import Election, BallotArchive, VoterList, Ballot, Voter
from demos_voting.ballot_distributor.serializers import VoterSerializer
from demos_voting.ballot_distributor.utils.api import BulletinBoardAPISession
from demos_voting.base.utils import get_range_in_chunks

TASK_CONCURRENCY = getattr(settings, 'DEMOS_VOTING_TASK_CONCURRENCY', None) or multiprocessing.cpu_count()


# Ballot distribution phase tasks #############################################

@shared_task(ignore_result=True)
def prepare_ballot_distribution_phase(election_pk):
    """
    Prepare the election's ballot distribution phase.
    """
    with transaction.atomic():
        election = Election.objects.select_for_update().get(pk=election_pk)
        if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
            return
        assert election.state == election.STATE_BALLOT_DISTRIBUTION
        election.ballot_distribution_started_at = timezone.now()
        election.save()
    # Schedule the end of the ballot distribution phase.
    eta = election.voting_starts_at - datetime.timedelta(seconds=10)
    finalize_ballot_distribution_phase.apply_async(args=(election_pk,), eta=eta)


@shared_task(bind=True, ignore_result=True, max_retries=None, default_retry_delay=60)
def finalize_ballot_distribution_phase(self, election_pk):
    """
    Finalize the election's ballot distribution phase.
    """
    with transaction.atomic():
        election = Election.objects.select_for_update().get(pk=election_pk)
        if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
            return
        assert election.state == election.STATE_BALLOT_DISTRIBUTION
        # Delay the end of the ballot distribution phase until all submitted
        # tasks have completed. This may consume part of the voting period, in
        # that case the administrators will be responsible for extending it.
        ballot_archive_states = (BallotArchive.STATE_PENDING, BallotArchive.STATE_PROCESSING)
        ballot_archives = election.ballot_archives.filter(state__in=ballot_archive_states)
        voter_list_states = (VoterList.STATE_PENDING, VoterList.STATE_PROCESSING)
        voter_lists = election.voter_lists.filter(state__in=voter_list_states)
        if ballot_archives.exists() or voter_lists.exists():
            if timezone.now() > election.voting_ends_at:
                raise RuntimeError("The ballot distribution phase did not end in time for the voting phase.")
            raise self.retry()
        # Mark the end of the ballot distribution phase.
        election.state = election.STATE_COMPLETED
        election.ballot_distribution_ended_at = timezone.now()
        election.save()
    # Schedule deletion of the ballots after the end of the voting period.
    clean_up_ballot_distribution_phase.apply_async(args=(election_pk,), eta=election.voting_ends_at)


@shared_task(ignore_result=True)
def clean_up_ballot_distribution_phase(election_pk):
    """
    Delete the election's ballots.
    """
    election = Election.objects.get(pk=election_pk)
    assert election.state in (election.STATE_COMPLETED, election.STATE_FAILED, election.STATE_CANCELLED)
    for ballot in election.ballots.iterator():
        ballot.file.delete()
        ballot.delete()
    for ballot_archive in election.ballot_archives.iterator():
        ballot_archive.file.delete()


@task_failure.connect(sender=prepare_ballot_distribution_phase)
def prepare_ballot_distribution_task_failure(**kwargs):
    ballot_distribution_task_failure_handler(**kwargs)


@task_failure.connect(sender=finalize_ballot_distribution_phase)
def finalize_ballot_distribution_task_failure(**kwargs):
    ballot_distribution_task_failure_handler(**kwargs)


def ballot_distribution_task_failure_handler(**kwargs):
    election_pk = kwargs['kwargs'].get('election_pk', next(iter(kwargs['args']), None))
    with transaction.atomic():
        election = Election.objects.select_for_update().get(pk=election_pk)
        if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
            return
        assert election.state == election.STATE_BALLOT_DISTRIBUTION
        timezone_now = timezone.now()
        # Cancel all active ballot archive and voter list tasks.
        ballot_archive_states = (BallotArchive.STATE_PENDING, BallotArchive.STATE_PROCESSING)
        ballot_archives = election.ballot_archives.select_for_update().filter(state__in=ballot_archive_states)
        ballot_archives.update(state=BallotArchive.STATE_CANCELLED, processing_ended_at=timezone_now)
        voter_list_states = (VoterList.STATE_PENDING, VoterList.STATE_PROCESSING)
        voter_lists = election.voter_lists.select_for_update().filter(state__in=voter_list_states)
        voter_lists.update(state=VoterList.STATE_CANCELLED, processing_ended_at=timezone_now)
        # Mark the failure of the ballot distribution phase.
        election.state = election.STATE_FAILED
        election.ballot_distribution_ended_at = timezone_now
        election.save()


# Ballot archive tasks ########################################################

@shared_task(ignore_result=True)
def process_ballot_archive(ballot_archive_pk):
    """
    Prepare the processing of the ballot archive.
    """
    with transaction.atomic():
        ballot_archive = BallotArchive.objects.select_for_update().get(pk=ballot_archive_pk)
        if ballot_archive.state in (ballot_archive.STATE_FAILED, ballot_archive.STATE_CANCELLED):
            return
        assert ballot_archive.state == ballot_archive.STATE_PENDING
        ballot_archive.state = ballot_archive.STATE_PROCESSING
        ballot_archive.processing_started_at = timezone.now()
        ballot_archive.save()
    # Assign random ballots to the ballot archive. Do this in the database
    # level without fetching any objects.
    with transaction.atomic():
        # Randomly select the required number of unassigned ballots.
        ballots = Ballot.objects.filter(election_id=ballot_archive.election_id, archive=None, voter=None)
        ballots = ballots.select_for_update().order_by('?')[:ballot_archive.ballot_count]
        # Updating a query once a slice has been taken is not allowed, use a
        # nested query instead.
        Ballot.objects.filter(pk__in=ballots).update(archive=ballot_archive)
    # Start the ballot paper generation tasks.
    generate_ballot_archive_files_tasks = [
        generate_ballot_archive_files.si(ballot_archive_pk, range_start, range_stop)
        for range_start, range_stop in get_range_in_chunks(ballot_archive.ballot_count, TASK_CONCURRENCY)
    ]
    finalize_ballot_archive_task = finalize_ballot_archive.si(ballot_archive_pk=ballot_archive_pk)
    chord(generate_ballot_archive_files_tasks, finalize_ballot_archive_task).delay()


@shared_task
def generate_ballot_archive_files(ballot_archive_pk, range_start, range_stop):
    """
    Generate the specified ballots' papers.
    """
    ballot_archive = BallotArchive.objects.prefetch_related('election__questions__options').get(pk=ballot_archive_pk)
    if ballot_archive.state in (ballot_archive.STATE_FAILED, ballot_archive.STATE_CANCELLED):
        return
    assert ballot_archive.state == ballot_archive.STATE_PROCESSING
    # Generate the ballot papers' files.
    ballots = ballot_archive.ballots.all()[range_start: range_stop]
    for ballot in ballots.iterator():
        prefetch_related_objects([ballot], 'parts__questions__options')
        ballot.election = ballot_archive.election  # force-"prefetch" the election
        ballot.generate_file()


@shared_task(ignore_result=True)
def finalize_ballot_archive(ballot_archive_pk):
    """
    Finalize the processing of the ballot archive.
    """
    ballot_archive = BallotArchive.objects.get(pk=ballot_archive_pk)
    if ballot_archive.state in (ballot_archive.STATE_FAILED, ballot_archive.STATE_CANCELLED):
        return
    assert ballot_archive.state == ballot_archive.STATE_PROCESSING
    # Generate the ballot archive's file.
    ballot_archive.generate_file()
    # Finalize the ballot archive.
    with transaction.atomic():
        ballot_archive = BallotArchive.objects.select_for_update().get(pk=ballot_archive_pk)
        if ballot_archive.state in (ballot_archive.STATE_FAILED, ballot_archive.STATE_CANCELLED):
            return
        assert ballot_archive.state == ballot_archive.STATE_PROCESSING
        ballot_archive.state = ballot_archive.STATE_COMPLETED
        ballot_archive.processing_ended_at = timezone.now()
        ballot_archive.save()


@task_failure.connect(sender=process_ballot_archive)
def process_ballot_archive_task_failure(**kwargs):
    ballot_archive_task_failure_handler(**kwargs)


@task_failure.connect(sender=generate_ballot_archive_files)
def generate_ballot_archive_files_task_failure(**kwargs):
    ballot_archive_task_failure_handler(**kwargs)


@task_failure.connect(sender=finalize_ballot_archive)
def finalize_ballot_archive_task_failure(**kwargs):
    ballot_archive_task_failure_handler(**kwargs)


def ballot_archive_task_failure_handler(**kwargs):
    ballot_archive_pk = kwargs['kwargs'].get('ballot_archive_pk', next(iter(kwargs['args']), None))
    with transaction.atomic():
        ballot_archive = BallotArchive.objects.select_for_update().get(pk=ballot_archive_pk)
        if ballot_archive.state in (ballot_archive.STATE_FAILED, ballot_archive.STATE_CANCELLED):
            return
        assert ballot_archive.state in (ballot_archive.STATE_PENDING, ballot_archive.STATE_PROCESSING)
        ballot_archive.state = ballot_archive.STATE_FAILED
        ballot_archive.processing_ended_at = timezone.now()
        ballot_archive.save()
    # Stop the ballot distribution phase, too.
    ballot_distribution_task_failure_handler(args=(), kwargs={'election_pk': ballot_archive.election_id})


# Voter list tasks ############################################################

@shared_task(ignore_result=True)
def process_voter_list(voter_list_pk):
    """
    Prepare processing of the voter list.
    """
    with transaction.atomic():
        voter_list = VoterList.objects.select_for_update().get(pk=voter_list_pk)
        if voter_list.state in (voter_list.STATE_FAILED, voter_list.STATE_CANCELLED):
            return
        assert voter_list.state == voter_list.STATE_PENDING
        voter_list.state = voter_list.STATE_PROCESSING
        voter_list.processing_started_at = timezone.now()
        voter_list.save()
    if voter_list.file:
        # The voter list has an attached file, import the voters from the file.
        try:
            with transaction.atomic():
                # Lock the election object before adding any voters.
                list(Election.objects.select_for_update().filter(pk=voter_list.election_id).values('pk'))
                voter_count = voter_list.load_file()
        except ValidationError as e:
            with transaction.atomic():
                voter_list = VoterList.objects.select_for_update().get(pk=voter_list_pk)
                if voter_list.state == voter_list.STATE_PROCESSING:
                    voter_list.file.delete()
                    voter_list.error = e.message
                    voter_list.state = voter_list.STATE_FAILED
                    voter_list.processing_ended_at = timezone.now()
                    voter_list.save()
            # Notify the administrator that the voter list has errors.
            voter_list.administrator.send_voter_list_failed_mail(voter_list)
            return
    else:
        # The voter list does not have an attached file, this means that the
        # number of voters has already been validated and their objects have
        # been created.
        voter_count = voter_list.voters.count()
    # Start the ballot generation and distribution tasks.
    send_voter_list_mails_tasks = [
        send_voter_list_mails.si(voter_list_pk, range_start, range_stop)
        for range_start, range_stop in get_range_in_chunks(voter_count, TASK_CONCURRENCY)
    ]
    voter_list_pk_task = finalize_voter_list.si(voter_list_pk=voter_list_pk)
    chord(send_voter_list_mails_tasks, voter_list_pk_task).delay()


@shared_task
def send_voter_list_mails(voter_list_pk, range_start, range_stop):
    """
    Assign random ballots to the specified voters, generate the ballot papers
    and distribute the ballot papers via email.
    """
    voter_list = VoterList.objects.get(pk=voter_list_pk)
    if voter_list.state in (voter_list.STATE_FAILED, voter_list.STATE_CANCELLED):
        return
    assert voter_list.state == voter_list.STATE_PROCESSING
    election = Election.objects.prefetch_related('questions__options').get(pk=voter_list.election_id)
    with transaction.atomic():
        # Lock all the specified voter objects to ensure that they will not be
        # assigned multiple ballots if they appear in multiple voter lists. Do
        # this in a subquery to avoid fetching any results.
        voter_pks = voter_list.voters.values_list('pk', flat=True)[range_start: range_stop]
        Voter.objects.filter(pk__in=Voter.objects.select_for_update().filter(pk__in=voter_pks)).exists()
        # Get only those voters who have not been assigned a ballot yet.
        voters = election.voters.filter(pk__in=voter_pks, ballot=None)
        voter_count = voters.count()
        if not voter_count:
            return
        # Randomly select the required number of unassigned ballots.
        ballots = election.ballots.filter(archive=None, voter=None).select_for_update().order_by('?')[:voter_count]
        # Ideally, generating the ballot papers, sending the emails and
        # updating the Bulletin Board should be done outside the transaction.
        # However the ballot and voter querysets would not be possible to be
        # used there because they would be re-evaluated and the former would
        # be empty and the latter would select new random ballots.
        with mail.get_connection() as connection, BulletinBoardAPISession() as s:
            # The ballot and the voter querysets may contain many objects and
            # are only evaluated at this point (without caching their results).
            for ballot, voter in zip(ballots.iterator(), voters.iterator()):
                # Assign the ballot to the voter.
                ballot.voter = voter
                ballot.save()
                # Generate the ballot paper and send it to the voter via email.
                prefetch_related_objects([ballot], 'parts__questions__options')
                voter.ballot.generate_file()
                voter.send_ballot_mail(connection=connection)
                # Send the voter object to the Bulletin Board.
                serializer = VoterSerializer(voter)
                r = s.post('elections/%s/voters/' % election.slug, json=serializer.data)
                r.raise_for_status()


@shared_task(ignore_result=True)
def finalize_voter_list(voter_list_pk):
    """
    Finalize processing of the voter list.
    """
    with transaction.atomic():
        voter_list = VoterList.objects.select_for_update().get(pk=voter_list_pk)
        if voter_list.state in (voter_list.STATE_FAILED, voter_list.STATE_CANCELLED):
            return
        assert voter_list.state == voter_list.STATE_PROCESSING
        voter_list.state = voter_list.STATE_COMPLETED
        voter_list.processing_ended_at = timezone.now()
        voter_list.save()


@task_failure.connect(sender=process_voter_list)
def process_voter_list_task_failure(**kwargs):
    voter_list_task_failure_handler(**kwargs)


@task_failure.connect(sender=send_voter_list_mails)
def send_voter_list_mails_task_failure(**kwargs):
    voter_list_task_failure_handler(**kwargs)


@task_failure.connect(sender=finalize_voter_list)
def finalize_voter_list_task_failure(**kwargs):
    voter_list_task_failure_handler(**kwargs)


def voter_list_task_failure_handler(**kwargs):
    voter_list_pk = kwargs['kwargs'].get('voter_list_pk', next(iter(kwargs['args']), None))
    with transaction.atomic():
        voter_list = VoterList.objects.select_for_update().get(pk=voter_list_pk)
        if voter_list.state in (voter_list.STATE_FAILED, voter_list.STATE_CANCELLED):
            return
        assert voter_list.state in (voter_list.STATE_PENDING, voter_list.STATE_PROCESSING)
        voter_list.state = voter_list.STATE_FAILED
        voter_list.processing_ended_at = timezone.now()
        voter_list.save()
    # Stop the ballot distribution phase, too.
    ballot_distribution_task_failure_handler(args=(), kwargs={'election_pk': voter_list.election_id})
