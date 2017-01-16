# File: apps.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import AppConfig
from django.core import checks
from django.db.models.signals import pre_delete

from demos_voting.common.checks import api_check, file_storage_check, security_check, privacy_check
from demos_voting.common.signals import pre_delete_protect_handler


class AppConfig(AppConfig):

    name = 'demos_voting.common'
    verbose_name = "Common package"

    def ready(self):
        super(AppConfig, self).ready()
        from demos_voting.common import tasks


class CommonMixin(object):

    def ready(self):
        super(CommonMixin, self).ready()

        # Register common checks

        checks.register(api_check, deploy=True)
        checks.register(file_storage_check)
        checks.register(privacy_check, deploy=True)
        checks.register(security_check, deploy=True)

        # Register common signal handlers

        Election = self.get_model('Election')
        pre_delete.connect(pre_delete_protect_handler, sender=Election,
                           dispatch_uid='election_pre_delete_protect_handler')

        # Abstract natural key dependencies. Ensure that the 'app_label' part
        # of natural key dependencies always exists (app_label.model_name).

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

