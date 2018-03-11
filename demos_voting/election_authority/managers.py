from __future__ import absolute_import, division, print_function, unicode_literals

from django.db import models


def _pre_save_source_mixin_factory(source):
    class PreSaveSourceMixin(object):
        """
        A related manager mixin that uses the `source` attribute of the
        reverse object as the source for the objects returned, only if the
        reverse object is not saved yet. This is required for generating the
        election/ballot attributes before the actual objects are saved in the
        database (e.g. for generating and previewing a ballot).
        """

        def all(self):
            if hasattr(self, 'instance') and self.instance.pk is None:
                # Only related managers have an `instance` attribute.
                objects = getattr(self.instance, source, None)
                if objects is not None:
                    return objects
            return super(PreSaveSourceMixin, self).all()

        def count(self):
            if hasattr(self, 'instance') and self.instance.pk is None:
                # Only related managers have an `instance` attribute.
                objects = getattr(self.instance, source, None)
                if objects is not None:
                    return len(objects)
            return super(PreSaveSourceMixin, self).count()

    return PreSaveSourceMixin


class ElectionQuestionManager(_pre_save_source_mixin_factory('_questions'), models.Manager):
    pass


class ElectionOptionManager(_pre_save_source_mixin_factory('_options'), models.Manager):
    pass


class BallotPartManager(_pre_save_source_mixin_factory('_parts'), models.Manager):
    pass


class BallotQuestionManager(_pre_save_source_mixin_factory('_questions'), models.Manager):
    pass


class BallotOptionManager(_pre_save_source_mixin_factory('_options'), models.Manager):
    pass
