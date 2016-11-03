# File: managers.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import apps
from django.db import models


class ElectionManager(models.Manager):

    def get_by_natural_key(self, e_id):
        return self.get(id=e_id)


class BallotManager(models.Manager):

    def count(self):
        try:
            return self.instance.ballot_cnt
        except AttributeError:
            return super(BallotManager, self).count()

    def get_queryset(self):

        app_config = apps.get_app_config(self.model._meta.app_label)

        Question = app_config.get_model('Question')
        PartQuestion = app_config.get_model('PartQuestion')

        partquestion_qs = PartQuestion.objects.select_related('question').defer(
            *['question__%s' % f.name for f in Question._meta.get_fields() if f.name != 'index']
        )

        ballot_qs = super(BallotManager, self).get_queryset().prefetch_related(
            models.Prefetch('parts__partquestions', partquestion_qs), 'parts__partquestions__options_c'
        )

        return ballot_qs

    def get_by_natural_key(self, e_id, b_serial_number):

        model = self.model._meta.get_field('election').related_model
        manager = model.objects.db_manager(self.db)
        election = manager.get_by_natural_key(e_id)

        return self.get(election=election, serial_number=b_serial_number)


class PartManager(models.Manager):

    def get_by_natural_key(self, e_id, b_serial_number, p_tag):

        model = self.model._meta.get_field('ballot').related_model
        manager = model.objects.db_manager(self.db)
        ballot = manager.get_by_natural_key(e_id, b_serial_number)

        return self.get(ballot=ballot, tag=p_tag)


class QuestionManager(models.Manager):

    def get_queryset(self):
        return super(QuestionManager, self).get_queryset().prefetch_related('options_p')

    def get_by_natural_key(self, e_id, q_index):

        model = self.model._meta.get_field('election').related_model
        manager = model.objects.db_manager(self.db)
        election = manager.get_by_natural_key(e_id)

        return self.get(election=election, index=q_index)


class OptionManager_P(models.Manager):

    def get_by_natural_key(self, e_id, q_index, o_index):

        model = self.model._meta.get_field('question').related_model
        manager = model.objects.db_manager(self.db)
        question = manager.get_by_natural_key(e_id, q_index)

        return self.get(question=question, index=o_index)


class OptionManager_C(models.Manager):

    def get_by_natural_key(self, e_id, b_serial_number, p_tag, q_index, o_index):

        model = self.model._meta.get_field('question').related_model
        manager = model.objects.db_manager(self.db)
        question = manager.get_by_natural_key(e_id, b_serial_number, p_tag, q_index)

        return self.get(question=question, index=o_index)


class PartQuestionManager(models.Manager):

    def get_by_natural_key(self, e_id, b_serial_number, p_tag, q_index):

        model = self.model._meta.get_field('part').related_model
        manager = model.objects.db_manager(self.db)
        part = manager.get_by_natural_key(e_id, b_serial_number, p_tag)

        model = self.model._meta.get_field('question').related_model
        manager = model.objects.db_manager(self.db)
        question = manager.get_by_natural_key(e_id, q_index)

        return self.get(part=part, question=question)


class TaskManager(models.Manager):

    def get_by_natural_key(self, e_id, task_id):

        model = self.model._meta.get_field('election').related_model
        manager = model.objects.db_manager(self.db)
        election = manager.get_by_natural_key(e_id)

        return self.get(election=election, task_id=task_id)


class PrivateApiUserManager(models.Manager):

    def get_by_natural_key(self, app_label):
        return self.get(app_label=app_label)


class PrivateApiNonceManager(models.Manager):

    def get_by_natural_key(self, app_label, nonce, timestamp, type):

        model = self.model._meta.get_field('user').related_model
        manager = model.objects.db_manager(self.db)
        user = manager.get_by_natural_key(app_label)

        return self.get(user=user, nonce=nonce, timestamp=timestamp, type=type)

