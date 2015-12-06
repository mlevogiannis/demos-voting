# File: config.py

from __future__ import absolute_import, division, unicode_literals

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

