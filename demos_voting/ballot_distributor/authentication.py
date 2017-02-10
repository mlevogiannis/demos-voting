# File: authentication.py

from __future__ import absolute_import, division, print_function, unicode_literals


from demos_voting.ballot_distributor.models import APIAuthNonce
from demos_voting.ballot_distributor.utils.api import APIUser
from demos_voting.base.authentication import APIAuthentication


class APIAuthentication(APIAuthentication):
    user_cls = APIUser
    auth_nonce_cls = APIAuthNonce

