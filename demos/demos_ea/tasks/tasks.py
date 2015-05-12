# File: tasks.py

import time
import hashlib
import tarfile

from io import BytesIO
from os import urandom
from math import ceil
from base64 import b64encode
from random import SystemRandom
from itertools import chain
from urllib.parse import urljoin

from django.db import models, transaction
from django.utils import translation
from django.db.models import Model
from django.db.models.query import QuerySet

from celery import shared_task, current_task
from celery.signals import task_failure

from demos_ea.tasks.pdf import BallotCreator
from demos_ea.tasks.crypto import CryptoClient
from demos_ea.models import Election, Ballot, Side, Question, Option, OptData, \
	Trustee, Task

from demos_utils.hash import create_hash
from demos_utils.enums import State
from demos_utils.forms import post
from demos_utils.base32cf import b32cf_encode, b32cf_decode
from demos_utils.serializers import JsonSerializer
from demos_utils.permutations import permutation
from demos_utils.settings import *


@shared_task(ignore_result=True)
def election_setup(election_id, title, start_datetime, end_datetime, ballots,
	language, trustee_list, question_list):
	
	translation.activate(language)
	
	sr = SystemRandom()
	js = JsonSerializer()
	cc = CryptoClient(CRYPTO_AF, CRYPTO_ADDR)
	bc = BallotCreator(election_id, question_list)
	
	trustees = len(trustee_list)
	questions = len(question_list)
	sides = len(SIDE_ID_LIST)
	
	# Initialize progress bar
	
	progress = {'current': 0, 'total': ballots * sides * questions}
	current_task.update_state(state='PROGRESS', meta=progress)
	
	# Function to serialize and send objects or querysets to the other servers
	
	api_update_or_create_url = {srv: urljoin(URL[srv], "api/update_or_create/")
		for srv in ['abb', 'bds', 'vbb']}
	
	def api_update_or_create(object_or_queryset, file_data=None, **options):
		
		if isinstance(object_or_queryset, QuerySet):
			model_name = object_or_queryset.model.__name__
		else: # if isinstance(object_or_queryset, Model):
			model_name = object_or_queryset.__class__.__name__
		
		srv_list = (srv for srv in ['abb', 'bds', 'vbb']
			if model_name in JsonSerializer.srv_dict[srv])
		
		for srv in srv_list:
			text_data = js.serialize(object_or_queryset, srv=srv, **options)
			url = api_update_or_create_url[srv]
			post(url, text_data, file_data)
	
	# Create new election
	
	election = Election.objects.create(election_id=election_id,
		text=title, ballots=ballots, start_datetime=start_datetime,
		end_datetime=end_datetime, state=State.WORKING)
	
	api_update_or_create(election)
	
	# Insert trustees into the database
	
	trustee_buf = [Trustee(election=election, email=email)
		for email in trustee_list]
	
	Trustee.objects.bulk_create(trustee_buf)
	trustee_buf.clear()
	
	trustee_qs = Trustee.objects.filter(election=election)
	api_update_or_create(trustee_qs)
	
	# Insert questions into the database
	
	question_buf = []
	
	for question_id, (text,_,option_list) in enumerate(question_list, start=1):
		
		key = cc.gen_key(ballots, len(option_list))
		
		question = Question(election=election,
			question_id=question_id, text=text, key=key)
		
		question_buf.append(question)
	
	Question.objects.bulk_create(question_buf)
	question_buf.clear()
	
	question_qs = Question.objects.\
		filter(election=election).order_by('question_id')
	
	api_update_or_create(question_qs)
	
	# Insert options into the database
	
	option_buf = []
	
	for i, question in enumerate(question_qs):
		
		_, _, option_list = question_list[i]
		
		option_buf += [Option(question=question, text=option_text,
			order=order) for order, option_text in enumerate(option_list)]
		
	Option.objects.bulk_create(option_buf)
	option_buf.clear()
	
	option_qs = Option.objects.filter(question__election=election)
	api_update_or_create(option_qs)
	
	# Naming convention: suffix *_x_list indicates a list of elements of type x,
	# suffix *_xy_list indicates a list of elements of type x, each of which is
	# another list of elements of type y, where x, y can be one of b(allot),
	# s(ide) or q(uestion). While iterating over a *_xy_list, a *_iy_list is
	# the current iteration's inner list.
	
	for lo in range(100, ballots + 100, BATCH_SIZE):
		
		hi = lo + min(BATCH_SIZE, ballots+100-lo)
		
		# Insert ballots into the database
		
		ballot_buf = []
		credential_b_list = []
		
		for ballot_id in range(lo, hi):
			
			credential = urandom(CREDENTIAL_BYTES)
			
			credential_b_list.append(credential)
			credential_hash = create_hash(credential)
			
			ballot = Ballot(election=election,
				ballot_id=ballot_id, credential_hash=credential_hash)
			
			ballot_buf.append(ballot)
		
		Ballot.objects.bulk_create(ballot_buf)
		ballot_buf.clear()
		
		ballot_qs = Ballot.objects.filter(election=election,
			ballot_id__range=(lo, hi-1)).order_by('ballot_id')
		
		# Insert sides into the database
		
		side_buf = []
		permindex_s_list = []
		
		for ballot in ballot_qs:
			
			for side_id in SIDE_ID_LIST:
				
				permindex = int.from_bytes(urandom(PERMINDEX_BYTES), 'big')
				permindex = permindex >> PERMINDEX_SHIFT_BITS
				permindex = b32cf_encode(permindex).zfill(PERMINDEX_LEN)
				
				permindex_s_list.append(permindex)
				permindex_hash = create_hash(permindex)
				
				side = Side(ballot=ballot,
					side_id=side_id, permindex_hash=permindex_hash)
				
				side_buf.append(side)
		
		Side.objects.bulk_create(side_buf)
		side_buf.clear()
		
		side_qs = Side.objects.filter(ballot__election=election,
			ballot__ballot_id__range=(lo, hi-1)).\
			order_by('ballot__ballot_id', 'side_id')
		
		# Generate crypto data for all questions
		
		crypto_q_list = []
		 
		for question in question_qs:
			
			key = question.key
			options = question.option_set.count()
			
			crypto_q_list.append(cc.gen_ballot(key, ballots, options, hi-lo))
			
		# Iterate over all sides
		
		vcrec_s_list = []
		
		for s, (side, permindex) in enumerate(zip(side_qs, permindex_s_list)):
			
			vcrec_iq_list = []
			
			for question, crypto_s_list in zip(question_qs, crypto_q_list):
				
				crypto_list = crypto_s_list[s]
				
				question_id = question.question_id
				options = question.option_set.count()
				
				# Generate votecodes and receipts
				
				vcrec_list = []
				
				for votecode in range(options):
					
					receipt = int.from_bytes(urandom(RECEIPT_BYTES), 'big')
					receipt = receipt >> RECEIPT_SHIFT_BITS
					receipt = b32cf_encode(receipt).zfill(RECEIPT_LEN)
					
					vcrec_list.append((votecode, receipt))
				
				sr.shuffle(vcrec_list)
				
				# SJCL bitArrays need to be multiples of 32-bit words
				
				permindex_int = b32cf_decode(permindex)
				
				b1_len = 4*ceil(ceil(permindex_int.bit_length()/8)/4)
				b2_len = 4*ceil(ceil(question_id.bit_length()/8)/4)
				
				b1 = permindex_int.to_bytes(b1_len, 'big')
				b2 = question_id.to_bytes(b2_len, 'big')
				
				# Get the n-th permutation, where n is the sha256 hash of the
				# side's permindex concatenated with the question's id
				
				hash_value = hashlib.new(HASH_ALG_NAME, b1 + b2).digest()
				permindex_val = int.from_bytes(hash_value, 'big')
				
				perm_list = map(chain.from_iterable,zip(crypto_list,vcrec_list))
				perm_list = permutation(perm_list, permindex_val)
				
				# Insert optdata into the database
				
				optdata_buf = [OptData(side=side, question=question, com=com,
					decom=decom, zk1=zk1, zk_state=zk_state, votecode=votecode,
					receipt=receipt, order=order) for order, (com, decom, zk1,
					zk_state, votecode, receipt) in enumerate(perm_list)]
				
				OptData.objects.bulk_create(optdata_buf)
				optdata_buf.clear()
				
				# Update progress status
				
				progress['current'] += 1
				current_task.update_state(state='PROGRESS', meta=progress)
				
				vcrec_iq_list.append(vcrec_list)
			vcrec_s_list.append(vcrec_iq_list)
		
		optdata_qs = OptData.objects.filter(side__ballot__election=election,
			side__ballot__ballot_id__range=(lo, hi-1))
		
		crypto_q_list.clear()
		
		# Cluster permindex and votecode-receipt lists into 'sides'-length
		# groups (lists of sides to lists of sides per ballot)
		
		vcrec_bs_list = zip(*[iter(vcrec_s_list)]*sides)
		permindex_bs_list = zip(*[iter(permindex_s_list)]*sides)
		
		# Generate PDFs and store them in a tar file
		
		tarbuf = BytesIO()
		tar = tarfile.open(fileobj=tarbuf, mode='w:bz2')
		
		voteurl_s_list = []
		
		for ballot_id, b_credential, permindex_is_list, vcrec_is_list in zip(
			range(lo, hi), credential_b_list, permindex_bs_list, vcrec_bs_list):
			
			# Voteurl structure: ballot_id, credential, side_id, permindex_list
			
			voteurl_is_list = []
			b_ballot_id = ballot_id.to_bytes(BALLOT_ID_BYTES, 'big')
			
			for side_id in SIDE_ID_LIST:
				
				# Get the permindexes of all other sides
				
				other_permindex = (permindex for other_side_id, permindex \
					in zip(SIDE_ID_LIST, permindex_is_list) \
					if other_side_id != side_id)
				
				permindex_list = []
				
				for permindex in other_permindex:
					
					permindex = b32cf_decode(permindex)
					permindex = permindex.to_bytes(PERMINDEX_BYTES, 'big')
					permindex_list.append(permindex)
				
				b_side_id = side_id.encode().zfill(SIDE_ID_BYTES)
				b_permindex = b''.join(permindex_list)
				
				# Construct and encode the voteurl
				
				voteurl = b_ballot_id + b_credential + b_side_id + b_permindex
				voteurl = int.from_bytes(voteurl, 'big')
				voteurl = b32cf_encode(voteurl)
				
				voteurl_is_list.append(voteurl)
			
			voteurl_s_list.extend(voteurl_is_list)
			
			# Generate PDF ballot
			
			pdfbuf = bc.gen_ballot(ballot_id, permindex_is_list, \
				voteurl_is_list, vcrec_is_list)
			
			# Add PDF to tar file
			
			tarinfo = tarfile.TarInfo()
			
			tarinfo.name = "{0}.pdf".format(ballot_id)
			tarinfo.size = len(pdfbuf.getvalue())
			tarinfo.mtime = time.time()
			
			pdfbuf.seek(0)
			tar.addfile(tarinfo=tarinfo, fileobj=pdfbuf)
		
		tar.close()
		
		# Serialize and send database objects to the other servers
		
		api_update_or_create(ballot_qs, tarbuf, extra_fields={'pdf':
			["{0}.pdf".format(ballot_id) for ballot_id in range(lo, hi)]})
		
		api_update_or_create(side_qs, extra_fields=\
			{'permindex': permindex_s_list, 'voteurl': voteurl_s_list})
		
		api_update_or_create(optdata_qs)
		
		# TODO: move serialization and crypto data generation to subtasks
	
	# Update election state
	
	election.state = State.STARTED
	election.save(update_fields=['state'])
	api_update_or_create(election)#, fields=['state'])
	
	Task.objects.get(election_id=election_id).delete()
	
	translation.deactivate()


@task_failure.connect
def election_setup_failure_handler(*args, **kwargs):
	pass # TODO: database cleanup

