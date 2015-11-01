# File: apps.py

from django.apps import AppConfig as _AppConfig
from django.utils.translation import ugettext_lazy as _
from django.core import checks as _checks

class AppConfig(_AppConfig):
    name = 'demos.apps.ea'
    verbose_name = _('Election Authority')


@_checks.register(deploy=True)
def crypto_connectivity_check(app_configs, **kwargs):
    """Tests basic socket connectivity with crypto service
    """

    import socket
    from demos.common.utils import config

    try:
        af = getattr(socket, config.CRYPTO_AF)
        sock = socket.socket(af)
        
        sock.settimeout(config.RECV_TIMEOUT)
        sock.connect(config.CRYPTO_ADDR)
        
        sock.sendall('') # write something, will test +w flag on sockets
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
        return [ _checks.Info("Checking connectivity with crypto: \"%s\" OK" % \
                                config.CRYPTO_ADDR) ]
    except Exception, e:
        return [_checks.Error("Connectivity with crypto \"%s\" failed: %s" % \
                                ( config.CRYPTO_ADDR, e),
                              hint="Check that crypto service is running, properly configured")
                ]

#eof
