from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.utils import translation

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from demos_voting.base.utils import get_site_url


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return getattr(settings, 'ACCOUNT_IS_OPEN_FOR_SIGNUP', True)

    def get_logout_redirect_url(self, request):
        logout_redirect_url = super(AccountAdapter, self).get_logout_redirect_url(request)
        return get_site_url(request) if logout_redirect_url == '/' else logout_redirect_url

    def render_mail(self, template_prefix, email, context):
        try:
            language = EmailAddress.objects.get(email__iexact=email).user.profile.language
        except EmailAddress.DoesNotExist:
            language = None
        if not language:
            language = translation.get_language()
        with translation.override(language):
            return super(AccountAdapter, self).render_mail(template_prefix, email, context)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        return getattr(settings, 'SOCIALACCOUNT_IS_OPEN_FOR_SIGNUP', True)
