from __future__ import absolute_import, division, print_function, unicode_literals

import requests

from allauth.account.models import EmailAddress

from django.db import transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from demos_voting.base.signals import setup_ended, setup_started
from demos_voting.election_authority.models import Administrator, Election, Trustee
from demos_voting.election_authority.serializers import ElectionSerializer
from demos_voting.election_authority.tasks import prepare_setup_phase
from demos_voting.election_authority.utils.api import (
    BallotDistributorAPISession, BulletinBoardAPISession, VoteCollectorAPISession,
)


# Election state signals ######################################################

@receiver(setup_ended, sender=Election, dispatch_uid='%s.end_setup_phase' % __name__)
def end_setup_phase(election, **kwargs):
    try:
        # Notify the other servers that the setup phase has ended. Do this is
        # in reverse order to ensure that the Ballot Distributor will start the
        # next phase only after the Vote Collector and the Bulletin Board have
        # been successfully notified.
        api_session_classes = [BallotDistributorAPISession, VoteCollectorAPISession, BulletinBoardAPISession]
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
    for election_user_model in (Administrator, Trustee):
        election_user_model.objects.filter(email__iexact=instance.email).update(user=user)


@receiver(pre_delete, sender=EmailAddress, dispatch_uid='%s.update_election_user_on_email_address_delete' % __name__)
def update_election_user_on_email_address_delete(instance, **kwargs):
    for election_user_model in (Administrator, Trustee):
        election_user_model.objects.filter(email__iexact=instance.email).update(user=None)
