# File: dbsetup.py

from __future__ import division

import itertools
from django.db import transaction


@transaction.atomic
def election(*args):
    
    election = None
    
    if len(args) == 2:
        election_obj, app_config = args
    elif len(args) == 3:
        election, election_obj, app_config = args
    
    if not election:
        
        # Create new election
    
        Election = app_config.get_model('Election')
        kwargs = _prep_kwargs(election_obj, Election)
        election = Election.objects.create(**kwargs)
    
    # Insert trustees into the database
    
    try:
        Trustee = app_config.get_model('Trustee')
    except LookupError:
        pass
    else:
        trustee_buf = []
        
        for trustee_obj in election_obj['__list_Trustee__']:
            
            kwargs = _prep_kwargs(trustee_obj, Trustee)
            trustee = Trustee(election=election, **kwargs)
            trustee.full_clean()
            trustee_buf.append(trustee)
        
        Trustee.objects.bulk_create(trustee_buf)
        del trustee_buf
    
    # Insert questions into the database
    
    try:
        Question = app_config.get_model('Question')
    except LookupError:
        pass
    else:
        question_buf = []
        
        for question_obj in election_obj['__list_Question__']:
            
            kwargs = _prep_kwargs(question_obj, Question)
            question = Question(election=election, **kwargs)
            question.full_clean()
            question_buf.append(question)
        
        Question.objects.bulk_create(question_buf)
        del question_buf
        
        question_qs = Question.objects.filter(election=election)
    
    # Insert options into the database
    
    try:
        OptionC = app_config.get_model('OptionC')
    except LookupError:
        pass
    else:
        optionc_buf = []
        
        for question, question_obj in zip(question_qs.iterator(), \
            election_obj['__list_Question__']):
            
            for optionc_obj in question_obj['__list_OptionC__']:
                
                kwargs = _prep_kwargs(optionc_obj, OptionC)
                optionc = OptionC(question=question, **kwargs)
                optionc.full_clean()
                optionc_buf.append(optionc)
        
        OptionC.objects.bulk_create(optionc_buf)
        del optionc_buf


@transaction.atomic
def ballot(election_obj, app_config):
    
    ballot_list = election_obj['__list_Ballot__']
    _serial_list = [ballot_obj['serial'] for ballot_obj in ballot_list]
    
    lo = min(_serial_list)
    hi = max(_serial_list) + 1
    
    # Get election, ballot and part models
    
    Election = app_config.get_model('Election')
    Ballot = app_config.get_model('Ballot')
    Part = app_config.get_model('Part')
    
    election = Election.objects.get(id=election_obj['id'])
    
    # Insert ballots into the database
    
    ballot_buf = []
    
    for ballot_obj in ballot_list:
        
        kwargs = _prep_kwargs(ballot_obj, Ballot)
        ballot = Ballot(election=election, **kwargs)
        ballot.full_clean()
        ballot_buf.append(ballot)
    
    Ballot.objects.bulk_create(ballot_buf)
    del ballot_buf
    
    ballot_qs = Ballot.objects.filter(election=election,
        serial__range=(lo, hi-1))
    
    # Insert ballot parts into the database
    
    part_buf = []
    
    for ballot, ballot_obj in zip(ballot_qs.iterator(), ballot_list):
        
        for part_obj in ballot_obj['__list_Part__']:
            
            kwargs = _prep_kwargs(part_obj, Part)
            part = Part(ballot=ballot, **kwargs)
            part.full_clean()
            part_buf.append(part)
    
    Part.objects.bulk_create(part_buf)
    del part_buf
    
    part_qs = Part.objects.filter(ballot__election=election,
        ballot__serial__range=(lo, hi-1))
    
    # Add question and part many-to-many relation
    
    try:
        Question = app_config.get_model('Question')
    except LookupError:
        pass
    else:
        part_list = list(part_qs)
        question_qs = Question.objects.filter(election=election)
        
        for question in question_qs:
            question.m2m_parts.add(*part_list)
        
    
    # Insert option votecodes into the database
    
    try:
        OptionV = app_config.get_model('OptionV')
    except LookupError:
        pass
    else:
        part_list = itertools.chain.from_iterable(
            [ballot_obj['__list_Part__'] for ballot_obj in ballot_list])
        
        for part, part_obj in zip(part_qs.iterator(), part_list):
        
            optionv_buf = []
        
            for question, question_obj in zip(question_qs.iterator(), \
                part_obj['__list_Question__']):
                
                for optionv_obj in question_obj['__list_OptionV__']:
                    
                    kwargs = _prep_kwargs(optionv_obj, OptionV)
                    optionv = OptionV(question=question, part=part, **kwargs)
                    optionv.full_clean()
                    optionv_buf.append(optionv)
        
            OptionV.objects.bulk_create(optionv_buf)
            del optionv_buf


def _prep_kwargs(model_obj, Model):
    
    kwargs = {
        field.name: model_obj[field.name]
        for field in Model._meta.get_fields()
        if field.name in model_obj
    }
    
    return kwargs

