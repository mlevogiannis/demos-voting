from __future__ import absolute_import, division, print_function, unicode_literals

import requests

from django.core.checks import Error, register

from demos_voting.vote_collector.utils.api import (
    BallotDistributorAPISession, BulletinBoardAPISession, ElectionAuthorityAPISession,
)


@register(deploy=True)
def api_connectivity_check(app_configs, **kwargs):
    """
    Check for API connectivity issues.
    """
    messages = []
    for api_session_class in [BallotDistributorAPISession, BulletinBoardAPISession, ElectionAuthorityAPISession]:
        with api_session_class() as s:
            try:
                r = s.get('_test/')
                r.raise_for_status()
                r = s.post('_test/', json={'key': 'value'})
                r.raise_for_status()
            except requests.exceptions.RequestException as e:
                error = Error(
                    id='vote_collector.E001',
                    msg="Connection to '%s' failed: %s" % (api_session_class.server_username, e),
                    hint="If this is an authentication issue, use the 'createsystemusers' management command to "
                         "create/update the system's users.",
                )
                messages.append(error)
    return messages
