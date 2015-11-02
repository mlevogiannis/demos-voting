# File: apps.py

from django.apps import AppConfig as _AppConfig
from django.utils.translation import ugettext_lazy as _
from django.core import checks as _checks

class AppConfig(_AppConfig):
    name = 'demos.apps.bds'
    verbose_name = _('Ballot Distribution Center')



@_checks.register(deploy=True)
def tar_storage_check(app_configs, **kwargs):
    """Tests basic socket connectivity with crypto service
    """

    from demos.common.utils import config
    import tempfile
    import os

    try:
        fd, path = tempfile.mkstemp(dir=config.TARSTORAGE_ROOT)
        os.close(fd)
        os.unlink(path)
        
        return []
    except Exception as e:
        return [_checks.Error("Tar storage \"%s\" check failed: %s" % \
                                (config.TARSTORAGE_ROOT, e),
                              hint="Check that directory exists and is writable")
                ]

#eof
