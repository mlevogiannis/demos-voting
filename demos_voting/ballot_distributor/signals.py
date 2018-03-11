from __future__ import absolute_import, division, print_function, unicode_literals

import requests

from allauth.account.models import EmailAddress

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from demos_voting.ballot_distributor.models import Administrator, Election, Voter
from demos_voting.ballot_distributor.serializers import ElectionSerializer
from demos_voting.ballot_distributor.tasks import prepare_ballot_distribution_phase
from demos_voting.ballot_distributor.utils.api import BulletinBoardAPISession, VoteCollectorAPISession
from demos_voting.base.signals import ballot_distribution_ended, ballot_distribution_started


# Election state signals ######################################################

@receiver(ballot_distribution_started, sender=Election, dispatch_uid='%s.start_ballot_distribution_phase' % __name__)
def start_ballot_distribution_phase(election, **kwargs):
    prepare_ballot_distribution_phase(election.pk)  # synchronous call


@receiver(ballot_distribution_ended, sender=Election, dispatch_uid='%s.end_ballot_distribution_phase' % __name__)
def end_ballot_distribution_phase(election, **kwargs):
    try:
        # Notify the other servers that the ballot distribution phase has
        # ended. Do this is in reverse order to ensure that the Vote Collector
        # will start the next phase only after the Bulleting Board has been
        # successfully notified.
        api_session_classes = [VoteCollectorAPISession, BulletinBoardAPISession]
        for api_session_class in reversed(api_session_classes):
            with api_session_class() as s:
                serializer = ElectionSerializer(instance=election, fields=['state'])
                r = s.patch('elections/%s/' % election.slug, json=serializer.data)
                r.raise_for_status()
    except requests.exceptions.RequestException:
        if election.state != election.STATE_FAILED:
            # Saving the election will call this signal handler again.
            election.state = election.STATE_FAILED
            election.save(update_fields=['state', 'updated_at'])


# Election user signals #######################################################

@receiver(post_save, sender=EmailAddress, dispatch_uid='%s.update_election_user_on_email_address_save' % __name__)
def update_election_user_on_email_address_save(instance, **kwargs):
    user = instance.user if instance.verified else None
    for election_user_model in (Administrator, Voter):
        election_user_model.objects.filter(email__iexact=instance.email).update(user=user)


@receiver(pre_delete, sender=EmailAddress, dispatch_uid='%s.update_election_user_on_email_address_delete' % __name__)
def update_election_user_on_email_address_delete(instance, **kwargs):
    for election_user_model in (Administrator, Voter):
        election_user_model.objects.filter(email__iexact=instance.email).update(user=None)
