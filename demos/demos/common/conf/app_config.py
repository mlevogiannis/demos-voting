# File: app_config.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import AppConfig
from django.db.models.signals import pre_delete

from demos.common.signals import pre_delete_protect_handler


class AppConfig(AppConfig):
    
    def ready(self):
        
        # Prevent deletion of Election objects
        
        Election = self.get_model('Election')
        pre_delete.connect(pre_delete_protect_handler, sender=Election,
                           dispatch_uid='election_pre_delete_protect_handler')
        
        # Abstract natural key dependencies. Add the 'app_label' part of a
        # dependency, if it is missing (app_label.model_name).
        
        for model in self.get_models():
            
            if hasattr(model, 'natural_key') and hasattr(model.natural_key, 'dependencies'):
                
                dependencies = []
                for dep in model.natural_key.dependencies:
                    if '.' not in dep:
                        dep = '%s.%s' % (self.label, dep)
                    dependencies.append(dep)
                
                if dependencies != model.natural_key.dependencies:
                    
                    # Add a proxy natural_key method, if the class does not
                    # define its own (i.e. inherits its parent's method)
                    
                    if 'natural_key' not in vars(model):
                        def natural_key(self, _model=model, *args, **kwargs):
                            return super(_model, self).natural_key(*args, **kwargs)
                        model.natural_key = natural_key
                    
                    try:
                        model.natural_key.dependencies = dependencies
                    except AttributeError:
                        model.natural_key.__func__.dependencies = dependencies

