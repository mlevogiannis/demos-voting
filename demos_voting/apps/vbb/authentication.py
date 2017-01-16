# File: authentication.py

from __future__ import absolute_import, division, print_function, unicode_literals


from demos_voting.apps.vbb.models import APIAuthNonce
from demos_voting.apps.vbb.utils.api import APIUser
from demos_voting.common.authentication import APIAuthentication


class APIAuthentication(APIAuthentication):
    user_cls = APIUser
    auth_nonce_cls = APIAuthNonce

