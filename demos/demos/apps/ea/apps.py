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


@_checks.register(deploy=True)
def crypto_ca_keys_check(app_configs, **kwargs):
    """Tests CA certificate and key configuration
    """

    import socket
    from OpenSSL import crypto
    from demos.common.utils import config
    from django.utils.encoding import force_bytes

    if not (config.CA_CERT_PEM and config.CA_PKEY_PEM):
        return [_checks.Warning("CA certificate and key are not configured, ballots will be unsigned",
                                hint="Generate a SSL certificate with CA scope and install it in config") ]

    try:
        with open(config.CA_CERT_PEM, 'r') as ca_file:
            ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, ca_file.read())
        
        with open(config.CA_PKEY_PEM, 'r') as ca_file:
            ca_pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, ca_file.read(), \
                force_bytes(config.CA_PKEY_PASSPHRASE))
        return []
    except Exception, e:
        return [_checks.Error("CA certificate and key \"%s\" \"%s\" fail: %s" % \
                                (config.CA_CERT_PEM, config.CA_PKEY_PEM, e),
                              hint="Check that crypto service is running, properly configured")
                ]

#eof
