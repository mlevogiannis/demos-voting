# File: apps.py

from __future__ import division, unicode_literals

from django.apps import AppConfig as _AppConfig
from django.utils.translation import ugettext_lazy as _
from django.core import checks as _checks

from demos.common.utils.config import registry
config = registry.get_config('bds')


class AppConfig(_AppConfig):
    name = 'demos.apps.bds'
    verbose_name = _('Ballot Distribution Center')



@_checks.register(deploy=True)
def tar_storage_check(app_configs, **kwargs):
    """Tests basic socket connectivity with crypto service
    """

    import tempfile
    import os

    try:
        fd, path = tempfile.mkstemp(dir=config.BALLOT_ROOT)
        os.close(fd)
        os.unlink(path)
        
        return []
    except Exception as e:
        return [_checks.Error("Tar storage \"%s\" check failed: %s" % \
                                (config.BALLOT_ROOT, e),
                              hint="Check that directory exists and is writable")
                ]

#eof
