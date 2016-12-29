# File: tasks.py

from __future__ import absolute_import, division, print_function, unicode_literals

import itertools
import logging

from multiprocessing.pool import ThreadPool

from django.conf import settings
from django.core import mail
from django.utils import timezone
from django.utils.six.moves import range, zip

from celery import shared_task
from celery.signals import task_failure

from demos_voting.apps.ea.models import Election, Ballot, Part, PQuestion, POption
from demos_voting.apps.ea.utils.mail import make_trustee_message

logger = logging.getLogger(__name__)


@shared_task(name='ea.setup_task', ignore_result=True)
def setup_task(election_id):
    election = Election.objects.prefetch_related('questions__options', 'trustees').get(id=election_id)

    election.state = Election.STATE_SETUP_STARTED
    election.setup_started_at = timezone.now()
    election.save(update_fields=['state', 'setup_started_at'])

    election.generate_keypair()
    election.generate_certificate()

    for question in election.questions.all():
        question.generate_trustee_keys()
        question.generate_commitment_key()

    async_result = None
    thread_pool = ThreadPool()

    def generate_ballot(ballot):
        ballot.generate_credential()
        for part in ballot.parts.all():
            part.generate_security_code()
        for part in ballot.parts.all():
            for p_question in part.questions.all():
                p_question.generate_zk()
                for p_option in p_question.options.all():
                    p_option.generate_votecode()
                    p_option.generate_receipt()
                    p_option.generate_commitment()
                    p_option.generate_zk1()

    for lo in range(100, election.ballot_count + 100, settings.DEMOS_VOTING_BATCH_SIZE):
        hi = lo + min(settings.DEMOS_VOTING_BATCH_SIZE, election.ballot_count + 100 - lo)

        Ballot.objects.bulk_create(
            Ballot(election=election, serial_number=serial_number)
            for serial_number in range(lo, hi)
        )

        ballots = Ballot.objects.filter(election=election, serial_number__range=(lo, hi-1)).only('pk')
        Part.objects.bulk_create(
            Part(ballot=ballot, tag=tag)
            for ballot in ballots
            for tag in (Part.TAG_A, Part.TAG_B)
        )

        parts = Part.objects.filter(ballot__in=ballots).only('pk')
        PQuestion.objects.bulk_create(
            PQuestion(part=part, question=question)
            for part in parts
            for question in election.questions.all()
        )

        p_questions = PQuestion.objects.filter(part__in=parts).only('pk')
        POption.objects.bulk_create(
            POption(question=p_question, index=index)
            for question, p_question in zip(itertools.cycle(election.questions.all()), p_questions)
            for index in range(question.options.count())
        )

        ballots = election.ballots.prefetch_related('parts__questions__options').filter(serial_number__range=(lo,hi-1))

        if async_result:
            async_result.wait()

        async_result = thread_pool.map_async(generate_ballot, ballots)

    async_result.wait()

    messages = [make_trustee_message(trustee, index) for index, trustee in enumerate(election.trustees.all())]
    mail.get_connection().send_messages(messages)

    election.state = Election.STATE_SETUP_ENDED
    election.setup_ended_at = timezone.now()
    election.save(update_fields=['state', 'setup_ended_at'])


@task_failure.connect(sender=setup_task)
def setup_failure(**kwargs):
    election_id = kwargs['kwargs'].get('election_id', kwargs['args'][0])
    election = Election.objects.get(id=election_id)
    election.ballots.all().delete()
    election.state = Election.STATE_FAILED
    election.save(update_fields=['state'])

