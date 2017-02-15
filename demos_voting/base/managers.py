# File: managers.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.db import models
from django.db.models.functions import Length


class ElectionManager(models.Manager):

    def get_queryset(self):
        return super(ElectionManager, self).get_queryset().order_by(Length('id'), 'id')

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

    def get_queryset(self):
        return super(PQuestionManager, self).get_queryset().annotate(index=models.F('question__index'))

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

    def get_by_natural_key(self, election_id, task_name, task_id):
        election_manager = self.model._meta.get_field('election').related_model.objects.db_manager(self.db)
        election = election_manager.get_by_natural_key(election_id)
        return self.get(election=election, name=task_name, id=task_id)


class APIAuthNonceManager(models.Manager):

    def get_by_natural_key(self, username, value, timestamp):
        return self.get(username=username, value=value, timestamp=timestamp)

