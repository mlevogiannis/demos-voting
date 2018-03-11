from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.contrib.auth import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import Signal, receiver
from django.utils import timezone, translation

from rest_framework.authtoken.models import Token

from demos_voting.base.models import UserProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL, dispatch_uid='create_user_profile_on_user_save')
def create_user_profile_on_user_save(instance, created, **kwargs):
    if created:
        UserProfile.objects.create(
            user=instance,
            language=translation.get_language(),
            timezone=timezone.get_current_timezone_name(),
        )


@receiver(user_logged_in, dispatch_uid='set_language_and_timezone_on_user_logged_in')
def set_language_and_timezone_on_user_logged_in(request, user, **kwargs):
    request.session[translation.LANGUAGE_SESSION_KEY] = user.profile.language
    request.session['timezone'] = user.profile.timezone


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token_on_user_save(instance, created, **kwargs):
    if created:
        Token.objects.create(user=instance)


setup_started = Signal(providing_args=['election'])
setup_ended = Signal(providing_args=['election'])
ballot_distribution_started = Signal(providing_args=['election'])
ballot_distribution_ended = Signal(providing_args=['election'])
voting_started = Signal(providing_args=['election'])
voting_ended = Signal(providing_args=['election'])
tally_started = Signal(providing_args=['election'])
tally_ended = Signal(providing_args=['election'])
