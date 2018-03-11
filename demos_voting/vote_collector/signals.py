from __future__ import absolute_import, division, print_function, unicode_literals

import requests

from allauth.account.models import EmailAddress

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from demos_voting.base.signals import voting_ended, voting_started
from demos_voting.vote_collector.models import Administrator, Election
from demos_voting.vote_collector.serializers import ElectionSerializer
from demos_voting.vote_collector.tasks import prepare_voting_phase
from demos_voting.vote_collector.utils.api import BulletinBoardAPISession


# Election state signals ######################################################

@receiver(voting_started, sender=Election, dispatch_uid='%s.start_voting_phase' % __name__)
def start_voting_phase(election, **kwargs):
    prepare_voting_phase(election.pk)  # synchronous call


@receiver(voting_ended, sender=Election, dispatch_uid='%s.end_voting_phase' % __name__)
def end_voting_phase(election, **kwargs):
    try:
        # Notify the Bulletin Board that the voting phase has ended.
        with BulletinBoardAPISession() as s:
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
    Administrator.objects.filter(email__iexact=instance.email).update(user=user)


@receiver(pre_delete, sender=EmailAddress, dispatch_uid='%s.update_election_user_on_email_address_delete' % __name__)
def update_election_user_on_email_address_delete(instance, **kwargs):
    Administrator.objects.filter(email__iexact=instance.email).update(user=None)
