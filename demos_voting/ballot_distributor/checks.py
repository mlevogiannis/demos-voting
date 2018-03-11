from __future__ import absolute_import, division, print_function, unicode_literals

import requests

from django.core.checks import Error, register

from demos_voting.ballot_distributor.utils.api import (
    BulletinBoardAPISession, ElectionAuthorityAPISession, VoteCollectorAPISession,
)


@register(deploy=True)
def api_connectivity_check(app_configs, **kwargs):
    """
    Check for API connectivity issues.
    """
    messages = []
    for api_session_class in [BulletinBoardAPISession, ElectionAuthorityAPISession, VoteCollectorAPISession]:
        with api_session_class() as s:
            try:
                r = s.get('_test/')
                r.raise_for_status()
                r = s.post('_test/', json={'key': 'value'})
                r.raise_for_status()
            except requests.exceptions.RequestException as e:
                error = Error(
                    id='ballot_distributor.E001',
                    msg="Connection to '%s' failed: %s" % (api_session_class.server_username, e),
                    hint="If this is an authentication issue, use the 'createsystemusers' management command to "
                         "create/update the system's users.",
                )
                messages.append(error)
    return messages
