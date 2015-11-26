# File: __init__.py

from __future__ import absolute_import, division, unicode_literals

from django.core import checks as _checks

@_checks.register(deploy=True)
def api_connectivity_check(app_configs, **kwargs):
    from django.apps import apps
    from demos.common.utils import api
    from django.conf import settings # MUST be lazy!

    # Dict of applications that connect to remote ones
    connectivity_list = {'ea': ['bds', 'abb', 'vbb'], 'abb': ['ea'],
                         'vbb': ['abb']
                         }
    messages = []
    if app_configs is None:
        app_configs = settings.DEMOS_APPS
    
    for local_app in app_configs:
        app_config = apps.get_app_config(local_app)
        ok_apps = []
        for remote in connectivity_list.get(local_app, []):
            try:
                 api.Session(remote, app_config)
                 ok_apps.append(remote)
            except Exception as e:
                messages.append(_checks.Error("Could not connect from %s to %s: %s" % \
                                                (local_app, remote, e),
                                              hint="Try running ./manage.py createusers_%s" % local_app))
        if ok_apps:
            messages.append(_checks.Info("Checking application %s: Login to %s OK" % \
                                            (local_app, ', '.join(ok_apps)),
                                        hint=None))

    return messages
