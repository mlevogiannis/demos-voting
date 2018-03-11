from __future__ import absolute_import, division, print_function, unicode_literals

from allauth.account.models import EmailAddress

from django.db import transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from demos_voting.base.signals import tally_started
from demos_voting.bulletin_board.models import Administrator, Election, Trustee, Voter
from demos_voting.bulletin_board.tasks import prepare_tally_phase


# Election state signals ######################################################

@receiver(tally_started, sender=Election, dispatch_uid='%s.start_tally_phase' % __name__)
def start_tally_phase(election, **kwargs):
    transaction.on_commit(lambda: prepare_tally_phase.delay(election.pk))


# Election user signals #######################################################

@receiver(post_save, sender=EmailAddress, dispatch_uid='%s.update_election_user_on_email_address_save' % __name__)
def update_election_user_on_email_address_save(instance, **kwargs):
    user = instance.user if instance.verified else None
    for election_user_model in (Administrator, Trustee, Voter):
        election_user_model.objects.filter(email__iexact=instance.email).update(user=user)


@receiver(pre_delete, sender=EmailAddress, dispatch_uid='%s.update_election_user_on_email_address_delete' % __name__)
def update_election_user_on_email_address_delete(instance, **kwargs):
    for election_user_model in (Administrator, Trustee, Voter):
        election_user_model.objects.filter(email__iexact=instance.email).update(user=None)
