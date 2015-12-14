# File: setup.py

from __future__ import absolute_import, division, unicode_literals

import hashlib
import hmac
import io
import logging
import math
import os
import random
import tarfile
import time

from functools import partial
from OpenSSL import crypto

from billiard.pool import Pool
from multiprocessing.pool import ThreadPool

from django.apps import apps
from django.conf import settings
from django.utils import translation
from django.utils.encoding import force_bytes
from django.utils.six.moves import range, zip, zip_longest

from celery import current_task, shared_task
from celery.signals import task_failure

from demos.apps.ea.models import Election, Task
from demos.apps.ea.tasks import cryptotools, pdf
from demos.apps.ea.tasks.masks import apply_mask
from demos.common.utils import api, base32cf, enums, hashers
from demos.common.utils.int import int_from_bytes, int_to_bytes
from demos.common.utils.permutation import permute
from demos.common.utils.setup import insert_into_db

logger = logging.getLogger(__name__)

app_config = apps.get_app_config('ea')
conf = app_config.get_constants_and_settings()


@shared_task(ignore_result=True)
def election_setup(election_obj, language):
    
    translation.activate(language)
    
    # Get election's model instance and update its state to WORKING
    
    election = Election.objects.get(id=election_obj['id'])
    
    election.state = enums.State.WORKING
    election.save(update_fields=['state'])
    
    election_obj['state'] = enums.State.WORKING
    
    # Election-specific vote-token bit lengths
    
    tag_bits = 1
    serial_bits = (election.ballot_cnt + 100).bit_length()
    credential_bits = conf.CREDENTIAL_LEN * 8
    security_code_bits = conf.SECURITY_CODE_LEN * 5
    token_bits = serial_bits + credential_bits + tag_bits + security_code_bits
    pad_bits = int(math.ceil(token_bits / 5)) * 5 - token_bits
    
    # Initialize common utilities
    
    rand = random.SystemRandom()
    hasher = hashers.PBKDF2Hasher()
    pdfcreator = pdf.BallotPDFCreator(election_obj)
    
    process_pool = Pool()
    thread_pool = ThreadPool(processes=4)
    
    # Establish sessions with the other servers
    
    api_session = {app_name: api.ApiSession(app_name, app_config)
        for app_name in ['abb', 'vbb', 'bds']}
    
    # Load CA's X.509 certificate and private key
    
    try:
        with open(conf.CA_CERT_PEM, 'r') as ca_file:
            ca_cert = crypto.load_certificate(crypto.FILETYPE_PEM, ca_file.read())
        
        with open(conf.CA_PKEY_PEM, 'r') as ca_file:
            ca_pkey=crypto.load_privatekey(crypto.FILETYPE_PEM, ca_file.read(),
                force_bytes(conf.CA_PKEY_PASSPHRASE))
        
    except (AttributeError, TypeError, IOError, OSError) as e:
        
        if not settings.DEVELOPMENT:
            raise
        
        self_signed = True
        logger.warning("No CA configured, generating self-signed receipts.")
        
    else:
        self_signed = False
    
    # Generate a new RSA key pair
    
    pkey = crypto.PKey()
    pkey.generate_key(crypto.TYPE_RSA, conf.PKEY_BIT_LEN)
    
    # Generate a new X.509 certificate
    
    cert = crypto.X509()
    
    if not self_signed:
        cert.set_issuer(ca_cert.get_subject())
        cert.set_subject(ca_cert.get_subject())
    
    cert.get_subject().CN = election.name[:64]
    
    if self_signed:
        cert.set_issuer(cert.get_subject())
    
    cert.set_version(3)
    cert.set_serial_number(base32cf.decode(election.id))
    
    cert.set_notBefore(force_bytes(election.starts_at.strftime('%Y%m%d%H%M%S%z')))
    cert.set_notAfter(force_bytes(election.ends_at.strftime('%Y%m%d%H%M%S%z')))
    
    cert.set_pubkey(pkey)
    cert.sign(ca_pkey if not self_signed else pkey, str('sha256'))
    
    certbuf = io.BytesIO(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    
    # Generate question keys
    
    for question_obj in election_obj['__list_Question__']:
        question_obj['key'] = cryptotools.gen_key(conf.ECC_CURVE)
    
    # Find the maximum number of options
    
    max_options = max([q_obj['option_cnt'] for q_obj in election_obj['__list_Question__']])
    
    # Populate local and remote databases
    
    files = {
        'abb': [
            ('cert.pem', certbuf)
        ]
    }
    
    insert_into_db(election_obj, app_config)
    
    _remote_app_setup_f = partial(_remote_app_setup, data=election_obj,
        files=files, api_session=api_session, url_path='api/setup/p1/')
    
    async_result1 = thread_pool.map_async(_remote_app_setup_f, ['abb', 'vbb', 'bds'])
    
    # Generate ballots in groups of BATCH_SIZE
    
    progress = {'current': 0, 'total': election.ballot_cnt * 2}
    current_task.update_state(state='PROGRESS', meta=progress)
    
    q_list = [(question_obj['key'], len(question_obj['__list_OptionC__']), 0)
              for question_obj in election_obj['__list_Question__']]
    
    async_result2 = thread_pool.apply_async(_gen_ballot_crypto,
        (q_list, min(conf.BATCH_SIZE, election.ballot_cnt)))
    
    for lo in range(100, election.ballot_cnt + 100, conf.BATCH_SIZE):
        
        hi = lo + min(conf.BATCH_SIZE, election.ballot_cnt + 100 - lo)
        
        # Get current batch's crypto elements and generate the next one's
        
        crypto_bsqo_list, _ = async_result2.get()
        
        if hi - 100 < election.ballot_cnt:
            async_result2 = thread_pool.apply_async(_gen_ballot_crypto,
                (q_list, min(conf.BATCH_SIZE, election.ballot_cnt + 100 - hi)))
        
        # Generate the rest data for all ballots and parts and store them in
        # lists of dictionaries. They will be used to populate the databases.
        
        ballot_list = []
        
        for serial, crypto_sqo_list in zip(range(lo, hi), crypto_bsqo_list):
            
            # Generate a random credential and compute its hash value
            
            credential = os.urandom(conf.CREDENTIAL_LEN)
            credential_int = int_from_bytes(credential, 'big')
            credential_hash = hasher.encode(credential)
            
            ballot_obj = {
                'serial': serial,
                'credential': credential,
                'credential_hash': credential_hash,
                '__list_Part__': [],
            }
            
            for p_tag, crypto_qo_list in zip(['A', 'B'], crypto_sqo_list):
                
                # Generate a random security code and compute its hash value
                # and its hash's hash value. The client will use the first hash
                # to access the votecodes (as a passphrase) and to verify the
                # security code. The second hash uses the first hash's salt,
                # reversed.
                
                security_code = base32cf.random(conf.SECURITY_CODE_LEN, urandom=True)
                
                hash, salt, _ = hasher.encode(security_code, split=True)
                security_code_hash2 = hasher.encode(hash, salt[::-1])
                
                # Prepare long votecodes' key, salt and iterations (if enabled)
                
                if election.vc_type == enums.VcType.SHORT:
                    
                    l_votecode_salt = ''
                    l_votecode_iterations = None
                    
                elif election.vc_type == enums.VcType.LONG:
                    
                    key = base32cf.decode(security_code)
                    bytes = int(math.ceil(key.bit_length() / 8))
                    key = int_to_bytes(key, bytes, 'big')
                    
                    l_votecode_salt = hasher.salt()
                    l_votecode_iterations = hasher.iterations
                
                # Pack ballot part's data
                
                part_obj = {
                    'tag': p_tag,
                    'security_code': security_code,
                    'security_code_hash2': security_code_hash2,
                    'l_votecode_salt': l_votecode_salt,
                    'l_votecode_iterations': l_votecode_iterations,
                    '__list_Question__': [],
                }
                
                for q_index, crypto_o_list in enumerate(crypto_qo_list):
                    
                    # Each ballot part's votecodes are grouped by question
                    
                    question_obj = {
                        'index': q_index,
                        '__list_OptionV__': [],
                    }
                    
                    # Generate short votecodes
                    
                    options = len(crypto_o_list)
                    
                    votecode_list = list(range(1, options + 1))
                    rand.shuffle(votecode_list)
                    
                    # Prepare options
                    
                    for votecode, (com, decom, zk1, zk_state) \
                        in zip_longest(votecode_list, crypto_o_list):
                        
                        # Each part's option can be uniquely identified by:
                        
                        optionv_id = (q_index * max_options) + votecode
                        
                        # Prepare long votecodes (if enabled) and receipt data
                        
                        if election.vc_type == enums.VcType.SHORT:
                            
                            l_votecode = ''
                            l_votecode_hash = ''
                            
                            receipt_data = optionv_id
                            
                        elif election.vc_type == enums.VcType.LONG:
                            
                            # Each long votecode is constructed as follows:
                            # hmac(security_code, credential + (question_index
                            # * max_options) + short_votecode), so that we get
                            # a unique votecode for each option in a ballot's
                            # part. All votecode hashes share the same salt.
                            
                            msg = credential_int + optionv_id
                            bytes = int(math.ceil(msg.bit_length() / 8))
                            msg = int_to_bytes(msg, bytes, 'big')
                            
                            hmac_obj = hmac.new(key, msg, hashlib.sha256)
                            digest = int_from_bytes(hmac_obj.digest(), 'big')
                            
                            l_votecode = base32cf.encode(digest)[-conf.VOTECODE_LEN:]
                            
                            l_votecode_hash, _, _ = hasher.encode(l_votecode,
                                l_votecode_salt, l_votecode_iterations, True)
                            
                            receipt_data = base32cf.decode(l_votecode)
                        
                        # Generate receipt (receipt_data is an integer)
                        
                        bytes = int(math.ceil(receipt_data.bit_length() / 8))
                        receipt_data = int_to_bytes(receipt_data, bytes, 'big')
                        receipt_data = crypto.sign(pkey, receipt_data, str('sha256'))
                        receipt_data = int_from_bytes(receipt_data, 'big')
                        
                        receipt_full = base32cf.encode(receipt_data)
                        receipt = receipt_full[-conf.RECEIPT_LEN:]
                        
                        # Pack optionv's data
                        
                        optionv_obj = {
                            'votecode': votecode,
                            'l_votecode': l_votecode,
                            'l_votecode_hash': l_votecode_hash,
                            'receipt': receipt,
                            'receipt_full': receipt_full,
                            'com': com,
                            'decom': decom,
                            'zk1': zk1,
                            'zk_state': zk_state,
                        }
                        
                        question_obj['__list_OptionV__'].append(optionv_obj)
                        
                    part_obj['__list_Question__'].append(question_obj)
                
                ballot_obj['__list_Part__'].append(part_obj)
            
            # Build the voter tokens for both parts
            
            for i, part_obj in enumerate(ballot_obj['__list_Part__']):
                
                # Get the other part's security_code
                
                other_part_obj = ballot_obj['__list_Part__'][1-i]
                security_code = base32cf.decode(other_part_obj['security_code'])
                
                # The voter token consists of two parts. The first part is the
                # ballot's serial number and credential and the part's tag,
                # XORed with the second part. The second part is the other
                # part's security code, bit-inversed. This is done so that the
                # tokens of the two parts appear to be completely different.
                
                p1 = ((serial << (tag_bits + credential_bits)) |
                    (int_from_bytes(credential, 'big') << tag_bits) | i)
                
                p2 = (~security_code) & ((1 << security_code_bits) - 1)
                
                p1_len = serial_bits + credential_bits + tag_bits
                p2_len = security_code_bits
                
                for i in range(0, p1_len, p2_len):
                    p1 ^= p2 << i
                
                p1 &= (1 << p1_len) - 1
                
                # Assemble the voter token and add random padding, if required
                
                p = (p1 << p2_len) | p2
                
                if pad_bits > 0:
                    p |= (rand.getrandbits(pad_bits) << token_bits)
                
                # Encode the voter token
                
                voter_token = base32cf.encode(p)
                voter_token = voter_token.zfill((token_bits + pad_bits) // 5)
                
                part_obj['voter_token'] = voter_token
            
            ballot_list.append(ballot_obj)
            
            # Update progress status
            
            progress['current'] += 1
            current_task.update_state(state='PROGRESS', meta=progress)
        
        # Generate PDF ballots and keep them in an in-memory tar file
        
        tarbuf = io.BytesIO()
        tar = tarfile.open(fileobj=tarbuf, mode='w:gz')
        
        _gen_ballot_pdf_f = partial(_gen_ballot_pdf, pdfcreator=pdfcreator)
        pdf_list = process_pool.map(_gen_ballot_pdf_f, ballot_list)
        
        for serial, pdfbuf in pdf_list:
            
            tarinfo = tarfile.TarInfo()
            
            tarinfo.name = "%s.pdf" % serial
            tarinfo.size = len(pdfbuf.getvalue())
            tarinfo.mtime = time.time()
            
            pdfbuf.seek(0)
            tar.addfile(tarinfo=tarinfo, fileobj=pdfbuf)
            
            # Update progress status
            
            progress['current'] += 1
            current_task.update_state(state='PROGRESS', meta=progress)
        
        tar.close()
        tarbuf.seek(0)
        
        # Get optionvs' permutations from the corresponding security codes
        
        for ballot_obj in ballot_list:
            
            for part_obj in ballot_obj['__list_Part__']:
                
                security_code = part_obj['security_code']
                
                for i, question_obj in enumerate(part_obj['__list_Question__']):
                    
                    optionv_list = question_obj['__list_OptionV__']
                    
                    # Get the n-th permutation of the optionv list, where
                    # n is the hash of the current part's security code plus
                    # the question's index, converted back to an integer.
                    
                    int_ = base32cf.decode(security_code) + i
                    bytes_ = int(math.ceil(int_.bit_length() / 8))
                    value = hashlib.sha256(int_to_bytes(int_, bytes_, 'big'))
                    p_index = int_from_bytes(value.digest(), 'big')
                    
                    optionv_list = permute(optionv_list, p_index)
                    
                    # Set the indices in proper order
                    
                    for o_index, optionv in enumerate(optionv_list):
                        optionv['index'] = o_index
                    
                    question_obj['__list_OptionV__'] = optionv_list
        
        # Populate local and remote databases
        
        data = {
            'id': election.id,
            '__list_Ballot__': ballot_list,
        }
        
        files = {
            'bds': [
                ('ballots.tar.gz', tarbuf)
            ]
        }
        
        insert_into_db(data, app_config)
        
        _remote_app_setup_f = partial(_remote_app_setup, data=data,
            files=files, api_session=api_session, url_path='api/setup/p2/')
        
        async_result1.wait()
        async_result1 = thread_pool.map_async(_remote_app_setup_f, ['abb', 'vbb', 'bds'])
    
    async_result1.wait()
    
    # Update election state to RUNNING
    
    election.state = enums.State.RUNNING
    election.save(update_fields=['state'])
    
    data = {
        'model': 'Election',
        'natural_key': {
            'e_id': election_obj['id']
        },
        'fields': {
            'state': election.state
        },
    }
    
    _remote_app_update_f = partial(_remote_app_update, data=data,
        api_session=api_session, url_path='api/update/')
    
    thread_pool.map(_remote_app_update_f, ['abb', 'vbb', 'bds'])
    
    # Delete celery task
    
    task = Task.objects.get(election=election)
    task.delete()
    
    translation.deactivate()


@task_failure.connect
def election_setup_failure_handler(*args, **kwargs):
    pass # TODO: database cleanup


def _remote_app_setup(app_name, **kwargs):
    
    # This function is used in a seperate thread.
    
    url_path = kwargs['url_path']
    api_session = kwargs['api_session']
    
    app_session = api_session[app_name]
    
    data = apply_mask(app_name, kwargs.get('data', {}))
    files = kwargs.get('files', {}).get(app_name)
    
    app_session.post(url_path, data, files, json=True)


def _remote_app_update(app_name, **kwargs):
    
    # This function is used in a seperate thread.
    
    url_path = kwargs['url_path']
    api_session = kwargs['api_session']
    
    app_session = api_session[app_name]
    app_session.post(url_path, kwargs['data'], json=True)


def _gen_ballot_crypto(q_list, number):
    
    # This function is used in a seperate thread.
    
    # Generate ballots' crypto elements and convert the returned list of
    # questions of ballots of parts of crypto elements to a list of ballots
    # of parts of questions of crypto elements
    
    opt_list = []
    blk_list = []
    
    for key, options, blanks in q_list:
        
        opts, blks = cryptotools.gen_ballot(key, options, blanks, number)
        
        opt_list.append(opts)
        blk_list.append(blks)
    
    opt_list = zip(*[iter([j for i in zip(*opt_list) for j in zip(*i)])] * 2)
    blk_list = zip(*[iter([j for i in zip(*blk_list) for j in zip(*i)])] * 2)
    
    return (opt_list, blk_list)


def _gen_ballot_pdf(ballot_obj, pdfcreator):
    
    # This function is used in a seperate process.
    
    serial = ballot_obj['serial']
    pdfbuf = pdfcreator.create(ballot_obj)
    
    return (serial, pdfbuf)

