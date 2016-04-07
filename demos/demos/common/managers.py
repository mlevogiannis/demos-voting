# File: managers.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.db import models
from django.utils import six
from django.utils.six.moves import range, zip

from demos.common.decorators import related_attr


class ElectionManager(models.Manager):
    
    def get_by_natural_key(self, e_id):
        return self.get(id=e_id)


class BallotManager(models.Manager):
    
    def count(self):
        try:
            return self.instance.ballot_cnt
        except AttributeError:
            return super(BallotManager, self).count()
    
    def get_by_natural_key(self, e_id, b_serial):
        
        model = self.model._meta.get_field('election').related_model
        manager = model.objects.db_manager(self.db)
        election = manager.get_by_natural_key(e_id)
        
        return self.get(election=election, serial=b_serial)


class PartManager(models.Manager):
    
    def get_by_natural_key(self, e_id, b_serial, p_tag):
        
        model = self.model._meta.get_field('ballot').related_model
        manager = model.objects.db_manager(self.db)
        ballot = manager.get_by_natural_key(e_id, b_serial)
        
        return self.get(ballot=ballot, tag=p_tag)


class QuestionManager(models.Manager):
    
    @related_attr('parts')
    def _annotate_with_related_pk(self, obj):
        self._related_part_pk = {'_related_part_pk': models.Value(obj.pk, output_field=obj._meta.pk)}
    
    def get_queryset(self):
        queryset = super(QuestionManager, self).get_queryset()
        if hasattr(self, '_related_part_pk'):
            queryset = queryset.annotate(**self._related_part_pk)
        return queryset
    
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
    
    def get_by_natural_key(self, e_id, b_serial, p_tag, q_index, o_index):
        
        model = self.model._meta.get_field('question').related_model
        manager = model.objects.db_manager(self.db)
        question = manager.get_by_natural_key(e_id, b_serial, p_tag, q_index)
        
        return self.get(question=question, index=o_index)


class PartQuestionManager(models.Manager):
    
    def get_by_natural_key(self, e_id, b_serial, p_tag, q_index):
        
        model = self.model._meta.get_field('part').related_model
        manager = model.objects.db_manager(self.db)
        part = manager.get_by_natural_key(e_id, b_serial, p_tag)
        
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

