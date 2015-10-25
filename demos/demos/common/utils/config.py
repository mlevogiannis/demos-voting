# File: config.py

TITLE_MAXLEN = 128    # chars
OPTION_MAXLEN = 128    # chars
QUESTION_MAXLEN = 128   # chars

RECEIPT_LEN = 10  # base32
VOTECODE_LEN = 16   # base32
CREDENTIAL_LEN = 8    # bytes
SECURITY_CODE_LEN = 8   # base32

HASH_LEN = 128   # chars

PKEY_BIT_LEN = 2048   # bits
PKEY_PASSPHRASE_LEN = 32   # base64
PKEY_PASSPHRASE_CIPHER = 'AES-128-CBC'  # openssl list-cipher-algorithms

# ------------------------------------------------------------------------------

import sys
from django.conf import settings

_config = sys.modules[__name__]

for iapp in settings.DEMOS_APPS:
    for key, value in settings.DEMOS_CONFIG[iapp].items():
        setattr(_config, key, value)


from django.core import checks as _checks

@_checks.register(deploy=True)
def api_connectivity_check(app_configs, **kwargs):
    from django.apps import apps
    from demos.common.utils import api
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
                 api.Session(local_app, remote, app_config)
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

@_checks.register(deploy=True)
def crypto_connectivity_check(app_configs, **kwargs):
    """Tests basic socket connectivity with crypto service
    """
    if 'ea' not in settings.DEMOS_APPS:
        return []

    import socket
    from demos.common.utils import crypto

    try:
        af = getattr(socket, _config.CRYPTO_AF)
        sock = socket.socket(af)
        
        sock.settimeout(_config.RECV_TIMEOUT)
        sock.connect(_config.CRYPTO_ADDR)
        
        sock.sendall('') # write something, will test +w flag on sockets
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()
        return [ _checks.Info("Checking connectivity with crypto: \"%s\" OK" % \
                                _config.CRYPTO_ADDR) ]
    except Exception as e:
        return [_checks.Error("Connectivity with crypto \"%s\" failed: %s" % \
                                ( _config.CRYPTO_ADDR, e),
                              hint="Check that crypto service is running, properly configured")
                ]


# eof
