# File: apps.py

from __future__ import absolute_import, division, unicode_literals

from demos.common.conf import AppConfig as _AppConfig
from django.utils.translation import ugettext_lazy as _


class AppConfig(_AppConfig):
    
    name = 'demos.apps.bds'
    verbose_name = _('Ballot Distribution Center')


from django.core import checks as _checks

@_checks.register(deploy=True)
def tar_storage_check(app_configs, **kwargs):
    """Tests basic socket connectivity with crypto service
    """

    import tempfile
    import os
    
    from django.apps import apps
    
    app_config = apps.get_app_config('bds')
    conf = app_conf.get_constants_and_settings()

    try:
        fd, path = tempfile.mkstemp(dir=conf.BALLOT_ROOT)
        os.close(fd)
        os.unlink(path)
        
        return []
    except Exception as e:
        return [_checks.Error("Tar storage \"%s\" check failed: %s" % \
                                (conf.BALLOT_ROOT, e),
                              hint="Check that directory exists and is writable")
                ]

#eof
