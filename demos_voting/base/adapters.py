from __future__ import absolute_import, division, print_function, unicode_literals

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    pass


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    pass
