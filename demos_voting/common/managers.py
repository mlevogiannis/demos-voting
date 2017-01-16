# File: managers.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.apps import apps
from django.db import models


class ElectionManager(models.Manager):

    def get_by_natural_key(self, election_id):
        return self.get(id=election_id)


class QuestionManager(models.Manager):

    def get_by_natural_key(self, election_id, question_index):

        election_manager = self.model._meta.get_field('election').related_model.objects.db_manager(self.db)
        election = election_manager.get_by_natural_key(election_id)

        return self.get(election=election, index=question_index)


class OptionManager(models.Manager):

    def get_by_natural_key(self, election_id, question_index, option_index):

        question_manager = self.model._meta.get_field('question').related_model.objects.db_manager(self.db)
        question = question_manager.get_by_natural_key(election_id, question_index)

        return self.get(question=question, index=option_index)


class BallotManager(models.Manager):

    def prefetch_related(self, *lookups):

        lookups = list(lookups)

        for i, lookup in enumerate(lookups):
            if lookup.startswith('parts__questions'):
                app_config = apps.get_app_config(self.model._meta.app_label)

                Question = app_config.get_model('Question')
                PQuestion = app_config.get_model('PQuestion')

                p_question_qs = PQuestion.objects.select_related('question').defer(
                    *['question__%s' % f.name for f in Question._meta.get_fields() if f.name != 'index']
                )

                lookups.insert(i, models.Prefetch('parts__questions', p_question_qs))
                break

        return super(BallotManager, self).prefetch_related(*lookups)

    def get_by_natural_key(self, election_id, ballot_serial_number):

        election_manager = self.model._meta.get_field('election').related_model.objects.db_manager(self.db)
        election = election_manager.get_by_natural_key(election_id)

        return self.get(election=election, serial_number=ballot_serial_number)


class PartManager(models.Manager):

    def get_by_natural_key(self, election_id, ballot_serial_number, part_tag):

        ballot_manager = self.model._meta.get_field('ballot').related_model.objects.db_manager(self.db)
        ballot = ballot_manager.get_by_natural_key(election_id, ballot_serial_number)

        return self.get(ballot=ballot, tag=part_tag)


class PQuestionManager(models.Manager):

    def get_by_natural_key(self, election_id, ballot_serial_number, part_tag, question_index):

        part_manager = self.model._meta.get_field('part').related_model.objects.db_manager(self.db)
        part = part_manager.get_by_natural_key(election_id, ballot_serial_number, part_tag)

        question_manager = self.model._meta.get_field('question').related_model.objects.db_manager(self.db)
        question = question_manager.get_by_natural_key(election_id, question_index)

        return self.get(part=part, question=question)


class POptionManager(models.Manager):

    def get_by_natural_key(self, election_id, ballot_serial_number, part_tag, question_index, option_index):

        p_question_manager = self.model._meta.get_field('question').related_model.objects.db_manager(self.db)
        p_question = p_question_manager.get_by_natural_key(election_id, ballot_serial_number, part_tag, question_index)

        return self.get(question=p_question, index=option_index)


class TaskManager(models.Manager):

    def get_by_natural_key(self, election_id, task_id):

        election_manager = self.model._meta.get_field('election').related_model.objects.db_manager(self.db)
        election = election_manager.get_by_natural_key(election_id)

        return self.get(election=election, task_id=task_id)


class APIAuthNonceManager(models.Manager):

    def get_by_natural_key(self, app_label, value, timestamp):
        return self.get(app_label=app_label, value=value, timestamp=timestamp)

