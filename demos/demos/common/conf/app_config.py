# File: app_config.py

from __future__ import absolute_import, division, unicode_literals

from django.apps import AppConfig as _AppConfig
from django.db.models.signals import pre_delete
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from demos.common.conf import constants
from demos.common.models.signals import pre_delete_protected_handler


class AppConfig(_AppConfig):
    
    def __init__(self, *args, **kwargs):
        
        super(AppConfig, self).__init__(*args, **kwargs)
        self._constants_and_settings = ConstantsAndSettings(self.label)
    
    def ready(self):
        
        Election = self.get_model('Election')
        pre_delete.connect(pre_delete_protected_handler, sender=Election)
    
    def get_constants_and_settings(self):
        
        return self._constants_and_settings


class ConstantsAndSettings(object):
    
    def __init__(self, app_label):
        
        self.app_label = app_label
        
        self._constants = {}
        
        for name in dir(constants):
            if name.isupper():
                self._constants[name] = getattr(constants, name)
        
        self._settings = dict(settings.DEMOS_CONFIG[self.app_label])
        
        self._settings['URL'] = settings.DEMOS_URL
        self._settings['API_URL'] = settings.DEMOS_API_URL
        
        self.__check_settings()
    
    def __getattr__(self, name):
        
        if name in self._constants:
            return self._constants[name]
        
        if name in self._settings:
            return self._settings[name]
        
        raise AttributeError("%s instance of app with label '%s' has no "
            "attribute '%s'" % (self.__class__.__name__, self.app_label, name))
    
    def __check_settings(self):
        
        for name in ('URL', 'API_URL'):
            for key, value in self._settings[name].items():
                if not value.endswith('/'):
                    raise ImproperlyConfigured("The value of 'DEMOS_%s.%s' "
                        "must end with a slash" % (name, key))
        
        name_clashes = set(self._constants.keys()) & set(self._settings.keys())
        
        if name_clashes:
            raise ImproperlyConfigured("Settings in 'DEMOS_CONFIG.%s' clash "
                "with constants of similar names from 'constants.py': %s" %
                (self.app_label, ', '.join(name_clashes)))

