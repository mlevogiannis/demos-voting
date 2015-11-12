# File: tasks.py

from __future__ import division

import io
import json
import hashlib
import logging

from base64 import b64decode
from celery import shared_task

from django.apps import apps
from django.core.files import File

from demos.apps.abb.models import Election, Question, Ballot, Part, OptionV, \
    Task

from demos.common.utils import api, crypto, enums, intc
from demos.common.utils.json import CustomJSONEncoder
from demos.common.utils.config import registry

logger = logging.getLogger(__name__)
app_config = apps.get_app_config('abb')
config = registry.get_config('abb')


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
            filter(index='B', optionv__voted=True).exists() else 0)
    
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
        
        com_sum = None
        
        for lo in range(100, election.ballots + 100, config.BATCH_SIZE):
            hi = lo + min(config.BATCH_SIZE, election.ballots + 100 - lo)
            
            # Grab all ballot parts that have options marked as 'voted'
            
            part_qs = Part.objects.filter(ballot__election=election, \
                ballot__serial__range=(lo,hi-1), optionv__voted=True).distinct()
            
            # Get com fields of the current ballot slice
            
            com_list = [] if com_sum is None else [com_sum]
            
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
            com_sum = r.json()
        
        # 'add_decom' task
        
        ballots = []
        
        # Grab all ballot parts that have options marked as 'voted'
        
        part_qs = Part.objects.filter(ballot__election=election, \
            optionv__voted=True).distinct()
        
        # Prepare 'ballots' data structure
        
        for part in part_qs.iterator():
            
            o_index_list = OptionV.objects.filter(question=question, \
                part=part, voted=True).values_list('index', flat=True)
            
            ballots.append((part.ballot.serial, part.index, list(o_index_list)))
        
        # Send request
        
        _request = request.copy()
        _request['ballots'] = ballots
        
        data = {
            'data': json.dumps(_request, separators=(',', ':'), \
                cls=CustomJSONEncoder)
        }
        
        r = ea_session.post('command/cryptotools/add_decom/', data)
        decom_sum = r.json()
        
        # 'verify_com' task, iff at least one ballot had been cast
        # An empty decom cannot be verified (False is always returned)
        
        if ballots:
        
            _request = request.copy()
            _request['com'] = com_sum
            _request['decom'] = decom_sum
            
            data = {
                'data': json.dumps(_request, separators=(',', ':'), \
                    cls=CustomJSONEncoder)
            }
            
            r = ea_session.post('command/cryptotools/verify_com/', data)
            verified = r.json()
            
            if not verified:
                logger.error('verify_com failed (election id: %s)'% election.id)
        
        # Save question's com_sum and decom_sum fields
        
        question.com_sum = com_sum
        question.decom_sum = decom_sum
        
        question.save(update_fields=['com_sum', 'decom_sum'])
        
        # Now, calculate votes
        
        ballots = election.ballots
        optionc_qs = question.optionc_set.all()
        
        decom = b64decode(decom_sum)
        
        pb_decom = crypto.Decom()
        pb_decom.ParseFromString(decom)
        
        msg = b64decode(pb_decom.msg)
        msg = intc.from_bytes(msg, byteorder='big')
        
        for optionc in optionc_qs:
            
            votes = msg % (ballots + 1)
            msg = (msg - votes) // (ballots + 1)
            
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
                
                ballots.append((part.ballot.serial, part.index, list(zk1_list)))
            
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
    
    # Import the ExportView here to avoid circular dependency error
    
    from demos.apps.abb.views import ExportView
    
    export = ExportView._export
    encoder = ExportView._CustomJSONEncoder
    
    del ExportView
    
    # Create an empty file and open it for writing, workaround for:
    # https://code.djangoproject.com/ticket/13809
    
    export_file = election.export_file
    
    export_file.save('export.json', File(io.BytesIO(b'')), save=False)
    export_file.close()
    
    export_file.file = export_file.storage.open(export_file.name, 'w')
    
    # Generate the json file
    
    # TODO: iterate over ballots and manually generate the file, otherwise a lot
    # of resources will be required for elections with many ballots and options
    
    data = export(['election'], {'Election': {'id': election_id}}, {}, 'export')
    json.dump(data, export_file, indent=4, sort_keys=True, cls=encoder)
    
    export_file.close()
    
    # Update election state
    
    election.state = enums.State.COMPLETED
    election.save(update_fields=['state', 'export_file'])
    
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
    
    task = Task.objects.get(election=election)
    task.delete()

