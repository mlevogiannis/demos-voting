# File: views.py

from __future__ import absolute_import, division, unicode_literals

import json
import logging
import math
import requests

from base64 import b64encode
from enum import IntEnum, unique

from django import http
from django.apps import apps
from django.db.models import Max
from django.core.exceptions import ValidationError
from django.middleware import csrf
from django.shortcuts import render, redirect
from django.utils import six, timezone
from django.utils.decorators import method_decorator
from django.utils.six.moves import range
from django.utils.six.moves.urllib.parse import quote, urljoin
from django.views.generic import View

from demos.apps.vbb.models import Election, Question, Ballot, Part, OptionV
from demos.common.utils import api, base32cf, enums, hashers, intc

logger = logging.getLogger(__name__)

app_config = apps.get_app_config('vbb')
conf = app_config.get_constants_and_settings()


class HomeView(View):
    
    template_name = 'vbb/home.html'
    
    def get(self, request):
        return render(request, self.template_name, {})


class VoteView(View):
    
    template_name = 'vbb/vote.html'
    
    class Error(Exception):
        pass
    
    @unique
    class State(IntEnum):
        INVALID_ELECTION_ID = 1
        INVALID_VOTE_TOKEN = 2
        ELECTION_NOT_STARTED = 3
        ELECTION_PAUSED = 4
        ELECTION_ENDED = 5
        BALLOT_USED = 6
        SERVER_ERROR = 7
        REQUEST_ERROR = 8
        CONNECTION_ERROR = 9
        NO_ERROR = 0
    
    @staticmethod
    def _parse_input(election_id, vote_token,):
        
        hasher = hashers.PBKDF2Hasher()
        
        retval = []
        
        # Get election from database
        
        try:
            election = Election.objects.get(id=election_id)
        except (ValidationError, Election.DoesNotExist):
            raise VoteView.Error(VoteView.State.INVALID_ELECTION_ID, *retval)
        
        retval.append(election)
        
        if election.state == enums.State.ERROR:
            raise VoteView.Error(VoteView.State.INVALID_ELECTION_ID, *retval)
        
        # Get question list from database
        
        try:
            question_qs = Question.objects.filter(election=election)
        except (ValidationError, Question.DoesNotExist):
            raise VoteView.Error(VoteView.State.SERVER_ERROR, *retval)
        
        retval.append(question_qs)
        
        # Verify election state
        
        now = timezone.now()
        
        if election.state == enums.State.WORKING or (election.state == \
            enums.State.RUNNING and now < election.starts_at):
            raise VoteView.Error(VoteView.State.ELECTION_NOT_STARTED, *retval)
        
        elif election.state == enums.State.RUNNING and now >= election.ends_at:
            raise VoteView.Error(VoteView.State.ELECTION_ENDED, *retval)
        
        elif election.state == enums.State.PAUSED:
            raise VoteView.Error(VoteView.State.ELECTION_PAUSED, *retval)
        
        elif election.state != enums.State.RUNNING:
            raise VoteView.Error(VoteView.State.SERVER_ERROR, *retval)
        
        # Vote token bits definitions
        
        index_bits = 1
        serial_bits = (election.ballot_cnt + 100).bit_length()
        credential_bits = conf.CREDENTIAL_LEN * 8
        security_code_bits = conf.SECURITY_CODE_LEN * 5
        token_bits = serial_bits+credential_bits+index_bits+security_code_bits
        
        # Verify vote token's length
        
        if not isinstance(vote_token, six.string_types):
            raise VoteView.Error(VoteView.State.INVALID_VOTE_TOKEN, *retval)
        
        if len(vote_token) != int(math.ceil(token_bits / 5)):
            raise VoteView.Error(VoteView.State.INVALID_VOTE_TOKEN, *retval)
        
        # The vote token consists of two parts. The first part is the
        # ballot's serial number and credential and the part's index,
        # XORed with the second part. The second part is the other
        # part's security code, bit-inversed. This is done so that the
        # tokens of the two parts appear to be completely different.
        
        try:
            p = base32cf.decode(vote_token) & ((1 << token_bits) - 1)
        except (AttributeError, TypeError, ValueError):
            raise VoteView.Error(VoteView.State.INVALID_VOTE_TOKEN, *retval)
        
        p1_len = serial_bits + credential_bits + index_bits
        p2_len = security_code_bits
        
        p1 = p >> p2_len
        p2 = p & ((1 << p2_len) - 1)
        
        for i in range(0, p1_len, p2_len):
            p1 ^= p2 << i
        
        p1 &= (1 << p1_len) - 1
        
        # Extract the selected part's serial number, credential and index and
        # the other part's security code
        
        serial = (p1 >> credential_bits + index_bits) & ((1 << serial_bits) - 1)
        
        credential = ((p1 >> index_bits) & ((1 << credential_bits) - 1))
        credential = intc.to_bytes(credential, conf.CREDENTIAL_LEN, 'big')
            
        index = 'A' if p1 & ((1 << index_bits) - 1) == 0 else 'B'
        
        security_code = base32cf.encode((~p2) & ((1 << security_code_bits) - 1))
        security_code = security_code.zfill(conf.SECURITY_CODE_LEN)
        
        # Get ballot object and verify credential
        
        try:
            ballot = Ballot.objects.get(election=election, serial=serial)
        except (ValidationError, Ballot.DoesNotExist):
            raise VoteView.Error(VoteView.State.INVALID_VOTE_TOKEN, *retval)
        
        retval.append(ballot)
        
        if not hasher.verify(credential, ballot.credential_hash):
            raise VoteView.Error(VoteView.State.INVALID_VOTE_TOKEN, *retval)
        
        # Get both part objects and verify the given security code. The first
        # matched object (part1) is always the part used by the client to vote,
        # the second matched object (part2) is the opposite part.
        
        order = ('' if index == 'A' else '-') + 'index'
        
        try:
            part_qs = Part.objects.filter(ballot=ballot).order_by(order)
        except (ValidationError, Part.DoesNotExist):
            raise VoteView.Error(VoteView.State.SERVER_ERROR, *retval)
        
        retval.append(part_qs)
        retval.append(b64encode(credential).decode())
        
        part2 = part_qs.last()
        
        _, salt, iterations = part2.security_code_hash2.split('$')
        hash, _, _ = hasher.encode(security_code, salt[::-1], iterations, True)
        
        if not hasher.verify(hash, part2.security_code_hash2):
            raise VoteView.Error(VoteView.State.INVALID_VOTE_TOKEN, *retval)
        
        retval.append(security_code)
        
        # Check if the ballot is already used
        
        if ballot.used:
            raise VoteView.Error(VoteView.State.BALLOT_USED, *retval)
        
        retval.append(now)
        
        return retval
    
    def get(self, request, **kwargs):
        
        election_id = kwargs.get('election_id')
        vote_token = kwargs.get('vote_token')
        
        # Normalize election_id and vote_token
        
        args = {
            'election_id': election_id,
            'vote_token': vote_token,
        }
        
        normalized = {
            'election_id': base32cf.normalize(election_id),
            'vote_token': base32cf.normalize(vote_token),
        }
        
        if args != normalized:
            return redirect('vbb:vote', **normalized)
        
        # Parse input 'election_id' and 'vote_token'. The first matched object
        # (part1) of part_qs is always the part used by the client to vote, the
        # second matched object (part2) is the other part. '_parse_input' method
        # raises a VoteView.Error exception for the first error that occurs.
        
        try:
            election, question_qs, ballot, (part1, _), credential, _, now = \
                VoteView._parse_input(election_id, vote_token)
        
        except VoteView.Error as e:
            
            status = 422
            args_len = len(e.args)
            now = timezone.now()
            
            context = {
                'state': e.args[0].value,
                'election': e.args[1] if args_len >= 2 else None,
                'questions': e.args[2] if args_len >= 3 else None,
                'b_serial': str(e.args[3].serial) if args_len >= 4 else None,
                'p_index': e.args[4].first().index if args_len >= 5 else None,
            }
        
        else:
            
            status = 200
            max_options = question_qs.aggregate(Max('option_cnt'))['option_cnt__max']
            abb_url = urljoin(conf.URL['abb'], quote('%s/' % election_id))
            security_code_hash2_split = part1.security_code_hash2.split('$')
            
            context = {
                'state': VoteView.State.NO_ERROR.value,
                'election': election,
                'questions': question_qs,
                'b_serial': str(ballot.serial),
                'p_index': part1.index,
                'abb_url': abb_url,
                'credential': credential,
                'votecode_len': conf.VOTECODE_LEN,
                'max_options': max_options,
                'sc_iterations': security_code_hash2_split[2],
                'sc_salt': security_code_hash2_split[1][::-1],
                'sc_length': conf.SECURITY_CODE_LEN,
            }
        
        context.update({
            'timezone_now': now,
            'VcType': { s.name: s.value for s in enums.VcType },
            'State': { s.name: s.value for s in VoteView.State },
        })
        
        csrf.get_token(request)
        return render(request, self.template_name, context, status=status)
    
    def post(self, request, **kwargs):
        
        hasher = hashers.PBKDF2Hasher()
        
        election_id = kwargs.get('election_id')
        vote_token = kwargs.get('vote_token')
        
        # Parse input 'election_id' and 'vote_token'. The first matched object
        # (part1) of part_qs is always the part used by the client to vote, the
        # second matched object (part2) is the other part. '_parse_input' method
        # raises a VoteView.Error exception for the first error that occurs.
        
        try:
             election, question_qs, ballot, part_qs, credential, \
                security_code,_ = VoteView._parse_input(election_id, vote_token)
        except VoteView.Error as e:
            return http.JsonResponse({'error': e.args[0].value}, status=422)
        
        part1, part2 = part_qs
        error = { 'error': VoteView.State.REQUEST_ERROR }
        
        # Load POST's json field
        
        json_field = request.POST.get('jsonfield')
        
        try:
            json_obj = json.loads(json_field);
        except (TypeError, ValueError):
            return http.JsonResponse(error, status=422)
        
        # Perform the requested action
        
        if json_obj.get('command') == 'verify-security-code':
            
            # The client sends the security code's hash in order to verify.
            # Since this acts as the password, the server stores the hash's
            # hash, which uses the hash's salt, but reversed.
            
            hash = json_obj.get('hash')
            
            if not isinstance(hash, six.string_types):
                return http.JsonResponse(error, status=422)
            
            if not hasher.verify(hash, part1.security_code_hash2):
                return http.HttpResponseForbidden()
            
            # Return a list of questions, where each question's element is a
            # list of (index, short_votecode) tuples. The client, who just
            # proved that knows the security code, is responsible for
            # restoring their correct order, using that security code.
            
            p1_votecodes = [
                (question.index, list(OptionV.objects.filter(part=part1,
                question=question).values_list('index', 'votecode')))
                for question in question_qs.iterator()
            ]
            
            return http.JsonResponse(p1_votecodes, safe=False)
        
        elif json_obj.get('command') == 'vote':
            
            vote_obj = json_obj.get('vote_obj')
            
            # Verify vote_obj's structure validity
            
            q_options = dict(question_qs.values_list('index', 'option_cnt'))
            
            vc_type = six.integer_types if election.vc_type == \
                enums.VcType.SHORT else six.string_types
            
            try:
                if not (isinstance(vote_obj, dict)
                    and len(vote_obj) == len(q_options)
                    and all(isinstance(q_index, six.string_types)
                    and isinstance(vc_list, list)
                    and 1 <= len(vc_list) <= q_options.get(int(q_index), -1)
                    and all(isinstance(vc, vc_type) for vc in vc_list)
                        for q_index, vc_list in vote_obj.items())):
                    
                    raise ValueError()
            
            except ValueError:
                # if q_index is a str but not a valid int, ValueError is raised
                return http.JsonResponse(error, status=422)
            
            except Exception:
                logger.exception('VoteView: Unexpected exception')
                return http.JsonResponse(error, status=422)
            
            # Verify votecodes, save vote and respond with the receipts
            
            response_obj = {}
            
            try:
                for question in question_qs.iterator():
                    
                    optionv_qs = OptionV.objects.\
                        filter(part=part1, question=question)
                    
                    vc_name = 'votecode'
                    vc_list = vote_obj[str(question.index)]
                    
                    # Long votecode version: use hashes instead of votecodes
                    
                    if election.vc_type == enums.VcType.LONG:
                        
                        vc_list = [hasher.encode(vc, part1.l_votecode_salt, \
                            part1.l_votecode_iterations, True)[0] \
                            for vc in vc_list]
                        
                        vc_name = 'l_' + vc_name + '_hash'
                    
                    # Get options for the requested votecodes
                    
                    vc_filter = {vc_name + '__in': vc_list}
                    
                    optionvs = dict(optionv_qs.filter(**vc_filter).\
                        values_list(vc_name, 'receipt'))
                    
                    # Return receipt list in the correct order
                    
                    receipt_list = [optionvs[vc] for vc in vc_list]
                    
                    # If lengths do not match, at least one votecode was invalid
                    
                    if len(receipt_list) != len(vc_list):
                        raise VoteView.Error(VoteView.State.REQUEST_ERROR)
                    
                    response_obj[str(question.index)] = receipt_list
                
                # Send vote data to the abb server
                
                abb_session = api.ApiSession('abb', app_config)
                
                data = {
                    'e_id': election.id,
                    'b_serial': ballot.serial,
                    'b_credential': credential,
                    'p1_index': part1.index,
                    'p1_votecodes': vote_obj,
                    'p2_security_code': security_code,
                }
                
                abb_session.post('api/vote/', data, json=True)
                
                ballot.used = True
                ballot.save(update_fields=['used'])
            
            except requests.exceptions.RequestException:
                return http.JsonResponse(error, status=422)
            
            except VoteView.Error as e:
                return http.JsonResponse({'error': e.args[0].value}, status=422)
            
            except Exception:
                logger.exception('VoteView: Unexpected exception')
                return http.JsonResponse(error, status=422)
            
            else:
                return http.JsonResponse(response_obj, safe=False)
        
        return http.JsonResponse(error, status=422)


class QRCodeScannerView(View):
    
    template_name = 'vbb/qrcode.html'
    
    def get(self, request):
        return render(request, self.template_name, {})


# API Views --------------------------------------------------------------------

class ApiSetupView(api.ApiSetupView):
    
    def __init__(self, *args, **kwargs):
        kwargs['app_config'] = app_config
        super(ApiSetupView, self).__init__(*args, **kwargs)
    
    @method_decorator(api.user_required('ea'))
    def dispatch(self, *args, **kwargs):
        return super(ApiSetupView, self).dispatch(*args, **kwargs)


class ApiUpdateView(api.ApiUpdateView):
    
    def __init__(self, *args, **kwargs):
        kwargs['app_config'] = app_config
        super(ApiUpdateView, self).__init__(*args, **kwargs)
    
    @method_decorator(api.user_required('ea'))
    def dispatch(self, *args, **kwargs):
        return super(ApiUpdateView, self).dispatch(*args, **kwargs)

