# File: tasks.py

import json
import hashlib
import logging

from base64 import b64decode
from celery import shared_task
from django.apps import apps

from demos.apps.abb.models import Election, Question, Ballot, Part, OptionV, \
    Task

from demos.common.utils import api, config, crypto, enums, intc
from demos.common.utils.json import CustomJSONEncoder

logger = logging.getLogger(__name__)
app_config = apps.get_app_config('abb')


@shared_task
def tally_protocol(election_id):
    
    election = Election.objects.get(id=election_id)
    
    ballot_qs = Ballot.objects.filter(election=election)
    question_qs = Question.objects.filter(election=election)
    
    ea_session = api.Session('ea', app_config)
    
    # Get election coins
    
    coins = ''
    
    for ballot in ballot_qs.iterator():
        coins += '%d' % (1 if ballot.part_set.\
            filter(tag='B', optionv__voted=True).exists() else 0)
    
    coins = coins.encode('ascii')
    coins = hashlib.sha256(coins).hexdigest()
    
    election.coins = coins
    election.save(update_fields=['coins'])
    
    # Perform 'add_com', 'add_decom' and 'verify_com' tasks
    
    for question in question_qs:
        
        request = {
            'e_id': election.id,
            'q_index': question.index,
            'key': question.key,
        }
        
        # 'add_com' task
        
        com = None
        
        for lo in range(100, election.ballots + 100, config.BATCH_SIZE):
            hi = lo + min(config.BATCH_SIZE, election.ballots + 100 - lo)
            
            # Grab all ballot parts that have options marked as 'voted'
            
            part_qs = Part.objects.filter(ballot__election=election, \
                ballot__serial__range=(lo,hi-1), optionv__voted=True).distinct()
            
            # Get com fields of the current ballot slice
            
            com_list = [] if com is None else [com]
            
            for part in part_qs.iterator():
                
                _com_list = OptionV.objects.filter(question=question, \
                    part=part, voted=True).values_list('com', flat=True)
                
                com_list.extend(_com_list)
            
            # Send request
            
            _request = request.copy()
            _request['com_list'] = com_list
            
            data = {
                'data': json.dumps(_request, separators=(',', ':'), \
                    cls=CustomJSONEncoder)
            }
            
            r = ea_session.post('command/cryptotools/add_com/', data)
            com = r.json()
        
        # 'add_decom' task
        
        ballots = []
        
        # Grab all ballot parts that have options marked as 'voted'
            
        part_qs = Part.objects.filter(ballot__election=election, \
            ballot__serial__range=(lo, hi-1), optionv__voted=True).distinct()
        
        # Prepare 'ballots' data structure
        
        for part in part_qs.iterator():
            
            index_list = OptionV.objects.filter(question=question, \
                part=part, voted=True).values_list('index', flat=True)
            
            ballots.append((part.ballot.serial, part.tag, list(index_list)))
        
        # Send request
        
        _request = request.copy()
        _request['ballots'] = ballots
        
        data = {
            'data': json.dumps(_request, separators=(',', ':'), \
                cls=CustomJSONEncoder)
        }
        
        r = ea_session.post('command/cryptotools/add_decom/', data)
        decom = r.json()
        
        # 'verify_com' task
        
        _request = request.copy()
        _request['com'] = com
        _request['decom'] = decom
        
        data = {
            'data': json.dumps(_request, separators=(',', ':'), \
                cls=CustomJSONEncoder)
        }
        
        r = ea_session.post('command/cryptotools/verify_com/', data)
        verified = r.json()
        
        # Save question's com, decom and verified fields
        
        question.com = com
        question.decom = decom
        question.verified = verified
        
        question.save(update_fields=['com', 'decom', 'verified'])
        
        # Now, count option votes
        
        ballots = election.ballots
        optionc_qs = question.optionc_set.all()
        
        decom = b64decode(decom)
        
        pb_decom = crypto.Decom()
        pb_decom.ParseFromString(decom)
        
        msg = b64decode(pb_decom.msg)
        msg = intc.from_bytes(msg, byteorder='big')
        
        for optionc in optionc_qs:
            
            votes = msg % (ballots + 1)
            msg = int((msg - votes) // (ballots + 1))
            
            optionc.votes = votes
            optionc.save(update_fields=['votes'])
    
    # Perform 'complete_zk' task
    
    for question in question_qs:
        
        request = {
            'e_id': election.id,
            'q_index': question.index,
            'key': question.key,
            'coins': election.coins,
        }
        
        for lo in range(100, election.ballots + 100, config.BATCH_SIZE):
            hi = lo + min(config.BATCH_SIZE, election.ballots + 100 - lo)
            
            # Grab all ballot parts
                
            part_qs = Part.objects.filter(ballot__election=election, \
                ballot__serial__range=(lo, hi-1)).distinct()
            
            # Prepare 'ballots' data structure
            
            ballots = []
            
            for part in part_qs:
                
                zk1_list = OptionV.objects.filter(part=part, \
                    question=question).values_list('zk1', flat=True)
                
                ballots.append((part.ballot.serial, part.tag, list(zk1_list)))
            
            # Send request
            
            request['ballots'] = ballots
            
            data = {
                'data': json.dumps(request, separators=(',', ':'), \
                    cls=CustomJSONEncoder)
            }
            
            r = ea_session.post('command/cryptotools/complete_zk/', data)
            ballot_part_zk2_lists = r.json()
            
            # Save zk2 fields
            
            for part, zk2_list in zip(part_qs, ballot_part_zk2_lists):
                
                optionv_qs = part.optionv_set.filter(question=question)
                
                for optionv, zk2 in zip(optionv_qs, zk2_list):
                    
                    optionv.zk2 = zk2
                    optionv.save(update_fields=['zk2'])
    
    # Update election state
    
    election.state = enums.State.COMPLETED
    election.save(update_fields=['state'])
    
    request = {
        'e_id': election.id,
        'state': election.state,
    }
    
    data = {
        'data': json.dumps(request, separators=(',', ':'), \
            cls=CustomJSONEncoder)
    }
    
    ea_session.post('command/updatestate/', data)
    
    # Delete celery task entry from the db
    
    task = Task.objects.get(election_id=election.id)
    task.delete()

