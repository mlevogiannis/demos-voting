# File: tasks.py

from __future__ import absolute_import, division, unicode_literals

import hashlib
import io
import json
import logging

from base64 import b64decode

from django.apps import apps
from django.core.files import File
from django.utils.six.moves import range, zip

from celery import shared_task

from demos.apps.abb.models import Election, Question, Ballot, Part, OptionV, Task
from demos.common.utils import api, crypto, enums

logger = logging.getLogger(__name__)

app_config = apps.get_app_config('abb')
conf = app_config.get_constants_and_settings()


@shared_task
def tally_protocol(election_id):
    
    election = Election.objects.get(id=election_id)
    
    ballot_qs = Ballot.objects.filter(election=election)
    question_qs = Question.objects.filter(election=election)
    
    ea_session = api.ApiSession('ea', app_config)
    
    # Get election coins
    
    coins = ''
    
    for ballot in ballot_qs.iterator():
        coins += '%d' % (1 if ballot.parts.filter(tag='B', optionv__voted=True).exists() else 0)
    
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
        
        combined_com = None
        
        for lo in range(100, election.ballots_cnt + 100, conf.BATCH_SIZE):
            hi = lo + min(conf.BATCH_SIZE, election.ballots_cnt + 100 - lo)
            
            # Grab all ballot parts that have options marked as 'voted'
            
            part_qs = Part.objects.distinct().filter(
                ballot__election=election,
                ballot__serial__range=(lo, hi-1),
                optionv__voted=True
            )
            
            # Get com fields of the current ballot slice
            
            com_list = [] if combined_com is None else [combined_com]
            
            for part in part_qs.iterator():
                
                _com_list = OptionV.objects.filter(question=question,
                    part=part, voted=True).values_list('com', flat=True)
                
                com_list.extend(_com_list)
            
            # Send request
            
            _request = request.copy()
            _request['com_list'] = com_list
            
            r = ea_session.post('api/crypto/add_com/', _request, json=True)
            combined_com = r.json()
        
        # 'add_decom' task
        
        ballots = []
        
        # Grab all ballot parts that have options marked as 'voted'
        
        part_qs = Part.objects.distinct().filter(
            ballot__election=election,
            optionv__voted=True
        )
        
        # Prepare 'ballots' data structure
        
        for part in part_qs.iterator():
            
            o_index_list = OptionV.objects.filter(question=question,
                part=part, voted=True).values_list('index', flat=True)
            
            ballots.append((part.ballot.serial, part.tag, list(o_index_list)))
        
        # Send request
        
        _request = request.copy()
        _request['ballots'] = ballots
        
        r = ea_session.post('api/crypto/add_decom/', _request, json=True)
        combined_decom = r.json()
        
        # 'verify_com' task, iff at least one ballot had been cast
        # An empty decom cannot be verified (False is always returned)
        
        if ballots:
        
            _request = request.copy()
            _request['com'] = combined_com
            _request['decom'] = combined_decom
            
            r = ea_session.post('api/crypto/verify_com/', _request, json=True)
            verified = r.json()
            
            if not verified:
                logger.error('verify_com failed (election id: %s)'% election.id)
        
        # Save question's combined_com and combined_decom fields
        
        question.combined_com = combined_com
        question.combined_decom = combined_decom
        
        question.save(update_fields=['combined_com', 'combined_decom'])
        
        # Now, calculate votes
        
        optionc_qs = question.options_c.all()
        
        decom = crypto.Decom()
        decom.ParseFromString(b64decode(combined_decom))
        
        assert len(optionc_qs) == len(decom.dp)
        
        for optionc, dp in zip(optionc_qs, decom.dp):
            
            optionc.votes = dp.msg
            optionc.save(update_fields=['votes'])
    
    # Perform 'complete_zk' task
    
    for question in question_qs:
        
        request = {
            'e_id': election.id,
            'q_index': question.index,
            'key': question.key,
            'coins': election.coins,
        }
        
        for lo in range(100, election.ballots_cnt + 100, conf.BATCH_SIZE):
            hi = lo + min(conf.BATCH_SIZE, election.ballots_cnt + 100 - lo)
            
            # Grab all ballot parts
                
            part_qs = Part.objects.distinct().filter(
                ballot__election=election,
                ballot__serial__range=(lo, hi-1)
            )
            
            # Prepare 'ballots' data structure
            
            ballots = []
            
            for part in part_qs:
                
                o_iz_list = list(OptionV.objects.filter(part=part,
                    question=question).values_list('index', 'zk1'))
                
                ballots.append((part.ballot.serial, part.tag, o_iz_list))
            
            # Send request
            
            request['ballots'] = ballots
            
            r = ea_session.post('api/crypto/complete_zk/', request, json=True)
            ballot_part_zk2_lists = r.json()
            
            # Save zk2 fields
            
            for part, zk2_list in zip(part_qs, ballot_part_zk2_lists):
                
                optionv_qs = part.options_v.filter(question=question)
                
                for optionv, zk2 in zip(optionv_qs, zk2_list):
                    
                    optionv.zk2 = zk2
                    optionv.save(update_fields=['zk2'])
    
    # Import the ApiExportView here to avoid circular dependency error
    
    from demos.apps.abb.views import ApiExportView
    
    export = ApiExportView._export
    encoder = ApiExportView._CustomJSONEncoder
    
    del ApiExportView
    
    # Create an empty file and open it for writing, workaround for:
    # https://code.djangoproject.com/ticket/13809
    
    export_file = election.export_file
    
    export_file.save('export.json', File(io.BytesIO(b'')), save=False)
    export_file.close()
    
    export_file.file = export_file.storage.open(export_file.name, 'w')
    
    # Generate the json file
    
    # TODO: iterate over ballots and manually generate the file, otherwise a lot
    # of resources will be required for elections with many ballots and options
    
    data = export(['election'], {'Election': {'id': election_id}}, {}, 'data')
    json.dump(data, export_file, indent=4, sort_keys=True, cls=encoder)
    
    export_file.close()
    
    # Update election state
    
    election.state = enums.State.COMPLETED
    election.save(update_fields=['state', 'export_file'])
    
    request = {
        'e_id': election.id,
        'state': election.state,
    }
    
    ea_session.post('api/updatestate/', request, json=True)
    
    # Delete celery task entry from the db
    
    task = Task.objects.get(election=election)
    task.delete()

