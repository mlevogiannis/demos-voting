# File: setup.py

from __future__ import absolute_import, division, unicode_literals

from itertools import chain
from operator import itemgetter

from django.db import transaction
from django.db.models.query import QuerySet
from django.utils.six.moves import zip


@transaction.atomic
def insert_into_db(election_obj, app_config):
    
    # Model: Election
    
    Election = app_config.get_model('Election')
    
    defaults = {field.name: election_obj[field.name]
                for field in Election._meta.get_fields()
                if field.name in election_obj}
    
    election, _ = Election.objects.get_or_create(id=defaults.pop('id'), defaults=defaults)
    
    # Insert trustees into the database
    
    if '__list_Trustee__' in election_obj:
        
        # Model: Trustee
        
        Trustee = app_config.get_model('Trustee')
        _bulk_create(Trustee, election, election_obj)
    
    # Insert questions and options into the database
    
    if '__list_Question__' in election_obj:
        
        # Model: Question
        
        Question = app_config.get_model('Question')
        _bulk_create(Question, election, election_obj)
        
        question_qs = Question.objects.filter(election=election)
        question_list = sorted(election_obj['__list_Question__'], key=itemgetter('index'))
        
        # Model: OptionC
        
        OptionC = app_config.get_model('OptionC')
        _bulk_create(OptionC, question_qs, question_list)
    
    # Insert ballots and parts into the database
    
    if '__list_Ballot__' in election_obj:
        
        # Model: Ballot
        
        Ballot = app_config.get_model('Ballot')
        _bulk_create(Ballot, election, election_obj)
        
        b_serial_list = [ballot_obj['serial'] for ballot_obj in election_obj['__list_Ballot__']]
        
        ballot_qs = Ballot.objects.filter(election=election, serial__in=b_serial_list)
        ballot_list = sorted(election_obj['__list_Ballot__'], key=itemgetter('serial'))
        
        # Model: Part
        
        Part = app_config.get_model('Part')
        _bulk_create(Part, ballot_qs, ballot_list)
        
        # Add questions's m2m relations and insert options into the database
        
        if '__list_Question__' in ballot_list[0]['__list_Part__'][0]:
            
            # Model: Part
            
            part_qs = Part.objects.filter(ballot__election=election, ballot__serial__in=b_serial_list)
            
            part_list = chain.from_iterable((sorted(ballot_obj['__list_Part__'],
                    key=itemgetter('index')) for ballot_obj in ballot_list))
            
            # Model: Question
            
            Question = app_config.get_model('Question')
            question_qs = Question.objects.filter(election=election)
            
            for question in question_qs:
                question.part_set.add(*list(part_qs))
            
            # Model: OptionV
            
            OptionV = app_config.get_model('OptionV')
            
            for part, part_obj in zip(part_qs.iterator(), part_list):
                
                question_list = sorted(part_obj['__list_Question__'], key=itemgetter('index'))
                _bulk_create(OptionV, question_qs, question_list, {'part': part})


def _bulk_create(model, mo_or_qs, obj_or_list, extra_kwargs={}):
    
    # mo: model object, qs: queryset,
    # obj: model dict, list: list of model dicts
    
    if isinstance(mo_or_qs, QuerySet):
        related_qs = mo_or_qs.iterator()
        related_list = obj_or_list
        related_model = mo_or_qs.model
    
    else: # isinstance(mo_or_qs, Model)
        related_qs = [ mo_or_qs ]
        related_list = [ obj_or_list ]
        related_model = mo_or_qs.__class__
    
    # Get the relation's name. Assumes that only one exists between the models.
    
    for f in model._meta.get_fields():
        if f.is_relation and f.related_model == related_model:
            relation_name = f.name
            break
    
    # Instatiate the new objects and bulk insert them into the database
    
    this_mo_list = []
    
    for related_mo, related_obj in zip(related_qs, related_list):
        
        for this_obj in related_obj['__list_' + model.__name__ + '__']:
            
            kwargs = {field.name: this_obj[field.name]
                      for field in model._meta.get_fields()
                      if field.name in this_obj}
            
            kwargs.update(extra_kwargs)
            kwargs[relation_name] = related_mo
            
            this_mo = model(**kwargs)
            this_mo.full_clean()
            
            this_mo_list.append(this_mo)
    
    model.objects.bulk_create(this_mo_list)
    del this_mo_list

