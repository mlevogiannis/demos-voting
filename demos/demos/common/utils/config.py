# File: config.py

from __future__ import division, unicode_literals

_CONFIG = {
    
    'TITLE_MAXLEN': 128,                      # chars
    'OPTION_MAXLEN': 128,                     # chars
    'QUESTION_MAXLEN': 128,                   # chars
    
    'RECEIPT_LEN': 10,                        # base32
    'VOTECODE_LEN': 16,                       # base32
    'CREDENTIAL_LEN': 8,                      # bytes
    'SECURITY_CODE_LEN': 8,                   # base32
    
    'CURVE': 1,
    'PKEY_BIT_LEN': 2048,                     # bits
    
    'HASH_FIELD_LEN': 128,                    # chars
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

# ------------------------------------------------------------------------------

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

@python_2_unicode_compatible
class ConfigBase(models.Model):
    
    key = models.CharField(max_length=128, unique=True)
    value = models.CharField(max_length=128)
    
    # Other model methods and meta options
    
    def __str__(self):
        return "%s - %s" % (self.key, self.value)
    
    class Meta:
        abstract = True
    
    class ConfigManager(models.Manager):
        def get_by_natural_key(self, key):
            return self.get(key=key)
    
    objects = ConfigManager()
    
    def natural_key(self):
        return (self.key,)

