# File: managers.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django.db import models
from demos.common.models.decorators import related


class ElectionManager(models.Manager):
    
    def get_by_natural_key(self, e_id):
        return self.get(id=e_id)


class QuestionCManager(models.Manager):
    
    def get_by_natural_key(self, e_id, q_index):
        
        model = self.model._meta.get_field('election').related_model
        manager = model.objects.db_manager(self.db)
        election = manager.get_by_natural_key(e_id)
        
        return self.get(election=election, index=q_index)


class OptionCManager(models.Manager):
    
    def get_by_natural_key(self, e_id, q_index, o_index):
        
        model = self.model._meta.get_field('question').related_model
        manager = model.objects.db_manager(self.db)
        question = manager.get_by_natural_key(e_id, q_index)
        
        return self.get(question=question, index=o_index)


class BallotManager(models.Manager):
        
    min_serial = 100
    
    @property
    @related('election')
    def max_serial(self):
        return self.min_serial + self.instance.ballots_cnt - 1
    
    @related('election')
    def chunks(self, size):
        for lo in range(self.min_serial, self.max_serial + 1, size):
            yield (lo, lo + min(size - 1, self.max_serial - lo))
    
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


class QuestionVManager(models.Manager):
    
    def get_by_natural_key(self, e_id, b_serial, p_tag, q_index):
        
        model = self.model._meta.get_field('part').related_model
        manager = model.objects.db_manager(self.db)
        part = manager.get_by_natural_key(e_id, b_serial, p_tag)
        
        model = self.model._meta.get_field('question').related_model
        manager = model.objects.db_manager(self.db)
        question = manager.get_by_natural_key(e_id, q_index)
        
        return self.get(part=part, question_c=question_c)


class OptionVManager(models.Manager):
    
    @property
    @related('question')
    def short_votecode_len(self):
        return len(six.text_type(self.instance.options_cnt))
    
    @property
    @related('question')
    def long_votecode_len(self):
        return self.instance.conf.long_votecode_len
    
    def get_by_natural_key(self, e_id, b_serial, p_tag, q_index, o_index):
        
        model = self.model._meta.get_field('question').related_model
        manager = model.objects.db_manager(self.db)
        question = manager.get_by_natural_key(e_id, b_serial, p_tag, q_index)
        
        return self.get(question=question, index=o_index)


class TrusteeManager(models.Manager):
    
    def get_by_natural_key(self, election_id, email):
        
        model = self.model._meta.get_field('election').related_model
        manager = model.objects.db_manager(self.db)
        election = manager.get_by_natural_key(election_id)
        
        return self.get(election=election, email=email)


class ConfManager(models.Manager):
    
    def get_by_natural_key(self, *args, **kwargs):
        
        fields = self.model._meta.unique_together[0]
        kwargs.update(dict(zip(fields, args)))
        
        return self.get(**kwargs)


class TaskManager(models.Manager):
    
    def get_by_natural_key(self, e_id, task_id):
        
        model = self.model._meta.get_field('election').related_model
        manager = model.objects.db_manager(self.db)
        election = manager.get_by_natural_key(e_id)
        
        return self.get(election=election, task_id=task_id)

