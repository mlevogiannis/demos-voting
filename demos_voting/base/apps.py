# File: apps.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import AppConfig
from django.core import checks
from django.db.models.signals import pre_delete
from django.utils import six
from django.utils.translation import ugettext_lazy as _

from demos_voting.base import tasks
from demos_voting.base.checks import api_check, file_storage_check, security_check, privacy_check
from demos_voting.base.signals import prevent_election_deletion


class AppConfig(AppConfig):

    name = 'demos_voting.base'
    verbose_name = _("DEMOS Voting: Base")


class CommonMixin(object):

    def ready(self):
        super(CommonMixin, self).ready()

        # Register common checks.

        checks.register(api_check, deploy=True)
        checks.register(file_storage_check)
        checks.register(privacy_check, deploy=True)
        checks.register(security_check, deploy=True)

        # Register common signal handlers.

        election_model = self.get_model('Election')
        pre_delete.connect(prevent_election_deletion, sender=election_model, dispatch_uid='prevent_election_deletion')

        # Abstract natural key dependencies: ensure that the 'app_label' part
        # of the of the natural key's dependency attribute always exists.
        # https://docs.djangoproject.com/en/dev/topics/serialization/#dependencies-during-serialization

        for model in self.get_models():
            if hasattr(model, 'natural_key') and hasattr(model.natural_key, 'dependencies'):
                changed = False
                dependencies = []
                for dependency in model.natural_key.dependencies:
                    if '.' not in dependency:
                        changed = True
                        dependency = '%s.%s' % (self.label, dependency)
                    dependencies.append(dependency)
                if changed:
                    if 'natural_key' not in vars(model):
                        # Add a proxy natural_key method, if the class does not
                        # define its own (i.e. inherits its parent's method).
                        def natural_key(self, _model=model, *args, **kwargs):
                            return super(_model, self).natural_key(*args, **kwargs)
                        model.natural_key = six.create_unbound_method(natural_key, model)
                    try:
                        model.natural_key.dependencies = dependencies
                    except AttributeError:
                        model.natural_key.__func__.dependencies = dependencies
