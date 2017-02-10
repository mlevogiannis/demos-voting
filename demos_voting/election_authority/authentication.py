# File: authentication.py

from __future__ import absolute_import, division, print_function, unicode_literals

from demos_voting.base.authentication import APIAuthentication
from demos_voting.election_authority.models import APIAuthNonce
from demos_voting.election_authority.utils.api import APIUser


class APIAuthentication(APIAuthentication):
    user_cls = APIUser
    auth_nonce_cls = APIAuthNonce

