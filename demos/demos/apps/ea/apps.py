# File: apps.py

from __future__ import absolute_import, division, unicode_literals

from demos.common.conf import AppConfig as _AppConfig
from django.utils.translation import ugettext_lazy as _


class AppConfig(_AppConfig):
    
    name = 'demos.apps.ea'
    verbose_name = _('Election Authority')


from django.core import checks as _checks

@_checks.register(deploy=True)
def crypto_connectivity_check(app_configs, **kwargs):
    """Tests basic socket connectivity with crypto service
    """

    import socket
    
    from django.apps import apps
    
    app_config = apps.get_app_config('ea')
    conf = app_config.get_constants_and_settings()

    try:
        af = getattr(socket, conf.CRYPTO_AF)
        sock = socket.socket(af)
        
        sock.settimeout(conf.RECV_TIMEOUT)
        sock.connect(conf.CRYPTO_ADDR)
        
        sock.sendall('') # write something, will test +w flag on sockets
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
        return [ _checks.Info("Checking connectivity with crypto: \"%s\" OK" % \
                                conf.CRYPTO_ADDR) ]
    except Exception as e:
        return [_checks.Error("Connectivity with crypto \"%s\" failed: %s" % \
                                ( conf.CRYPTO_ADDR, e),
                              hint="Check that crypto service is running, properly configured")
                ]


@_checks.register(deploy=True)
def crypto_ca_keys_check(app_configs, **kwargs):
    """Tests CA certificate and key configuration
    """

    import socket
    from OpenSSL import crypto
    from demos.common.utils.config import registry
    from django.utils.encoding import force_bytes
    from django.apps import apps
    
    app_config = apps.get_app_config('ea')
    conf = app_config.get_constants_and_settings()

    if not (conf.CA_CERT_PEM and conf.CA_PKEY_PEM):
        return [_checks.Warning("CA certificate and key are not configured, ballots will be unsigned",
                                hint="Generate a SSL certificate with CA scope and install it in config") ]

    try:
        with open(conf.CA_CERT_PEM, 'r') as ca_file:
            ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, ca_file.read())
        
        with open(conf.CA_PKEY_PEM, 'r') as ca_file:
            ca_pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, ca_file.read(), \
                force_bytes(conf.CA_PKEY_PASSPHRASE))
        return []
    except Exception as e:
        return [_checks.Error("CA certificate and key \"%s\" \"%s\" fail: %s" % \
                                (conf.CA_CERT_PEM, conf.CA_PKEY_PEM, e),
                              hint="Check that crypto service is running, properly configured")
                ]

#eof
