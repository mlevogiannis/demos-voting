from __future__ import absolute_import, division, print_function, unicode_literals

import multiprocessing

from celery import chord, shared_task
from celery.signals import task_failure

from django.conf import settings
from django.core import mail
from django.db import transaction
from django.utils import timezone

from six.moves import range

from demos_voting.base.utils import get_range_in_chunks
from demos_voting.election_authority.models import Ballot, BallotOption, BallotPart, BallotQuestion, Election
from demos_voting.election_authority.serializers import (
    BallotDistributorBallotSerializer, BulletinBoardBallotSerializer, ElectionSerializer, TrusteeSerializer,
    VoteCollectorBallotSerializer,
)
from demos_voting.election_authority.utils.api import (
    BallotDistributorAPISession, BulletinBoardAPISession, VoteCollectorAPISession,
)

TASK_CONCURRENCY = getattr(settings, 'DEMOS_VOTING_TASK_CONCURRENCY', None) or multiprocessing.cpu_count()


# Setup phase tasks ###########################################################

@shared_task(ignore_result=True)
def prepare_setup_phase(election_pk):
    """
    Prepare the election's setup phase.
    """
    with transaction.atomic():
        election = Election.objects.select_for_update().prefetch_related('trustees').get(pk=election_pk)
        if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
            return
        assert election.state == election.STATE_SETUP
        election.setup_started_at = timezone.now()
        election.save()
    # Generate the election's keys.
    election.generate_commitment_key()
    election.generate_private_key()
    election.generate_certificate()
    election.save(update_fields=['commitment_key', 'private_key_file', 'certificate_file'])
    # Send the election's objects to the other servers.
    for api_session_class in (BallotDistributorAPISession, VoteCollectorAPISession, BulletinBoardAPISession):
        with api_session_class() as s:
            serializer = ElectionSerializer(election)
            r = s.post('elections/', json=serializer.data)
            r.raise_for_status()
    # Generate the trustees' keys.
    for index, trustee in enumerate(election.trustees.all()):
        trustee.generate_secret_key(index)
        trustee.save()
    # Send the trustees to the Bulletin Board.
    with BulletinBoardAPISession() as s:
        serializer = TrusteeSerializer(election.trustees.all(), many=True)
        r = s.post('elections/%s/trustees/' % election.slug, json=serializer.data)
        r.raise_for_status()
    # Start the ballot generation tasks.
    generate_ballots_tasks = [
        generate_ballots.si(election_pk, range_start, range_stop)
        for range_start, range_stop in get_range_in_chunks(election.ballot_count, TASK_CONCURRENCY)
    ]
    finalize_setup_phase_task = finalize_setup_phase.si(election_pk=election_pk)
    chord_result = chord(generate_ballots_tasks, finalize_setup_phase_task).delay()
    # Register the ballot generation task group.
    group_result = chord_result.parent
    election.tasks.create(name='generate_ballots_task_group', result=group_result, task_id=group_result.id)


@shared_task(bind=True)
def generate_ballots(self, election_pk, range_start, range_stop):
    """
    Generate the ballots.
    """
    election = Election.objects.prefetch_related('questions__options').get(pk=election_pk)
    if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
        return
    assert election.state == election.STATE_SETUP
    # Generate the ballots. The ballots are not saved in the local database.
    # The ballots are sent to the other servers one by one, as a serialized
    # ballot can be up to a few megabytes long.
    for i, serial_number in enumerate(range(range_start + 100, range_stop + 100)):
        ballot = Ballot(election=election, serial_number=serial_number)
        ballot._parts = []
        for tag in (BallotPart.TAG_A, BallotPart.TAG_B):
            ballot_part = BallotPart(ballot=ballot, tag=tag)
            ballot_part.generate_credential()
            ballot_part.generate_credential_hash()
            ballot_part.generate_security_code()
            ballot_part._questions = []
            for election_question in election.questions.all():
                ballot_question = BallotQuestion(part=ballot_part, election_question=election_question)
                ballot_question.generate_zk1()
                ballot_question._options = []
                for index in range(election_question.option_count):
                    ballot_option = BallotOption(question=ballot_question, index=index)
                    ballot_option.generate_vote_code()
                    ballot_option.generate_vote_code_hash()
                    ballot_option.generate_receipt()
                    ballot_option.generate_commitment()
                    ballot_option.generate_zk1()
                    ballot_question._options.append(ballot_option)
                ballot_part._questions.append(ballot_question)
            ballot._parts.append(ballot_part)
        # Send the ballot's object to the other servers. Each server gets a
        # different subset of the ballot's attributes.
        api_classes = (
            (BallotDistributorAPISession, BallotDistributorBallotSerializer),
            (VoteCollectorAPISession, VoteCollectorBallotSerializer),
            (BulletinBoardAPISession, BulletinBoardBallotSerializer),
        )
        for api_session_class, ballot_serializer_class in api_classes:
            with api_session_class() as s:
                serializer = ballot_serializer_class(ballot, context={'election': election})
                r = s.post('elections/%s/ballots/' % election.slug, json=serializer.data)
                r.raise_for_status()
        # Update the task's progress.
        self.update_state(state='PROGRESS', meta={'current': i, 'total': range_stop - range_start})


@shared_task(ignore_result=True)
def finalize_setup_phase(election_pk):
    """
    Finalize the election's setup phase.
    """
    election = Election.objects.prefetch_related('trustees').get(pk=election_pk)
    if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
        return
    assert election.state == election.STATE_SETUP
    # Send the trustee keys.
    with mail.get_connection() as connection:
        for trustee in election.trustees.all():
            trustee.send_secret_key_mail(connection=connection)
    # Delete the election's private key and the trustees' secret keys.
    election.private_key_file.delete()
    election.trustees.update(secret_key=None)
    # Update the election's state.
    with transaction.atomic():
        election = Election.objects.select_for_update().get(pk=election_pk)
        if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
            return
        assert election.state == election.STATE_SETUP
        election.state = election.STATE_COMPLETED
        election.setup_ended_at = timezone.now()
        election.save()
    # Un-register the ballot generation task group.
    election.tasks.filter(name='generate_ballots_task_group').delete()


# Setup failure handlers ######################################################

@task_failure.connect(sender=prepare_setup_phase)
def prepare_setup_task_failure(**kwargs):
    setup_task_failure_handler(**kwargs)


@task_failure.connect(sender=generate_ballots)
def generate_ballots_task_failure(**kwargs):
    setup_task_failure_handler(**kwargs)


@task_failure.connect(sender=finalize_setup_phase)
def finalize_setup_task_failure(**kwargs):
    setup_task_failure_handler(**kwargs)


def setup_task_failure_handler(**kwargs):
    election_pk = kwargs['kwargs'].get('election_pk', next(iter(kwargs['args']), None))
    with transaction.atomic():
        election = Election.objects.select_for_update().get(pk=election_pk)
        if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
            return
        assert election.state == election.STATE_SETUP
        election.state = election.STATE_FAILED
        election.setup_ended_at = timezone.now()
        election.save()
    # Un-register the ballot generation task group.
    election.tasks.filter(name='generate_ballots_task_group').delete()
