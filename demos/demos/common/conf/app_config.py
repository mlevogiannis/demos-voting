# File: app_config.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import AppConfig
from django.db.models.signals import pre_delete
from django.utils.functional import lazy

from demos.common.signals import pre_delete_protect_handler


class AppConfig(AppConfig):
    
    def ready(self):
        
        # Prevent deletion of Election objects
        
        Election = self.get_model('Election')
        pre_delete.connect(pre_delete_protect_handler, sender=Election,
                           dispatch_uid='election_pre_delete_protect_handler')
        
        # Abstract natural key dependencies. If the 'app_label' part of a
        # dependency is missing (app_label.model_label), the lower-cased
        # name of the app they are contained within is added (it works like
        # model relationships on models that have not been defined yet).
        
        for model in self.get_models():
            
            if hasattr(model, 'natural_key') and hasattr(model.natural_key, 'dependencies'):
                
                dependencies = []
                for dep in model.natural_key.dependencies:
                    if '.' not in dep:
                        dep = '%s.%s' % (self.label.lower(), dep)
                    dependencies.append(dep)
                
                if dependencies != model.natural_key.dependencies:
                    
                    if 'natural_key' in vars(model):
                        natural_key = model.natural_key
                    else:
                        # Add a proxy natural_key method if the class does
                        # not define its own (i.e. inherits its parent's one)
                        natural_key = lazy(model.natural_key, tuple)
                        setattr(model, 'natural_key', natural_key)
                    
                    natural_key.dependencies = dependencies

