# File: config.py

_CONFIG = {
    
    'TITLE_MAXLEN': 128,                      # chars
    'OPTION_MAXLEN': 128,                     # chars
    'QUESTION_MAXLEN': 128,                   # chars
    
    'RECEIPT_LEN': 10,                        # base32
    'VOTECODE_LEN': 16,                       # base32
    'CREDENTIAL_LEN': 8,                      # bytes
    'SECURITY_CODE_LEN': 8,                   # base32
    
    'HASH_LEN': 128,                          # chars
    
    'PKEY_BIT_LEN': 2048,                     # bits
    'PKEY_PASSPHRASE_LEN': 32,                # base64
    'PKEY_PASSPHRASE_CIPHER': 'AES-128-CBC',  # openssl list-cipher-algorithms
}

# ------------------------------------------------------------------------------

from itertools import chain
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

class ConfigRegistry:
    
    def __init__(self, apps):
        self._configs = {}
        for app in apps:
            self._configs[app] = Config(app)
    
    def get_config(self, app):
        return self._configs[app]

class Config:
    
    def __init__(self, app):
        
        self.URL = settings.DEMOS_URL
        self.API_URL = settings.DEMOS_API_URL
        
        for k, v in chain(_CONFIG.items(), settings.DEMOS_CONFIG[app].items()):
            if hasattr(self, k):
                raise ImproperlyConfigured('Key "%s" is already configured' % k)
            setattr(self, k, v)

registry = ConfigRegistry(settings.DEMOS_APPS)

