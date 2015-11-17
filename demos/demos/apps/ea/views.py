# File: views.py

from __future__ import division, unicode_literals

import json
import random
import logging

from base64 import b64encode, b64decode

try:
    from urllib.parse import urljoin, quote
except ImportError:
    from urllib import quote
    from urlparse import urljoin

from django import http
from django.db import transaction
from django.apps import apps
from django.core import urlresolvers
from django.utils import translation, timezone
from django.shortcuts import render, redirect
from django.middleware import csrf
from django.views.generic import View
from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse

from celery.result import AsyncResult

from demos.apps.ea.forms import ElectionForm, OptionFormSet, \
    PartialQuestionFormSet, BaseQuestionFormSet
from demos.apps.ea.tasks import api_update, cryptotools, election_setup, pdf
from demos.apps.ea.models import Config, Election, OptionC, OptionV, Task

from demos.common.utils import api, base32cf, crypto, enums
from demos.common.utils.json import CustomJSONEncoder
from demos.common.utils.config import registry
from demos.common.utils.dbsetup import _prep_kwargs

logger = logging.getLogger(__name__)
app_config = apps.get_app_config('ea')
config = registry.get_config('ea')


class HomeView(View):
    
    template_name = 'ea/home.html'
    
    def get(self, request):
        return render(request, self.template_name, {})


class CreateView(View):
    
    template_name = 'ea/create.html'
    
    def get(self, request, *args, **kwargs):
        
        election_form = ElectionForm(prefix='election')
        
        # Get an empty question formset
        
        QuestionFormSet = PartialQuestionFormSet(formset=BaseQuestionFormSet)
        question_formset = QuestionFormSet(prefix='question')
        
        question_and_options_list = [(question_formset.empty_form, \
            OptionFormSet(prefix='option__prefix__'))]
        
        context = {
            'election_form': election_form,
            'question_formset': question_formset,
            'question_and_options_list': question_and_options_list,
        }
        
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        
        # Get the election form
        
        election_form = ElectionForm(request.POST, prefix='election')
        
        # "Peek" at the number of questions
        
        try:
            questions = int(request.POST['question-TOTAL_FORMS'])
            if questions < 1 or questions > config.MAX_QUESTIONS:
                raise ValueError
        except (ValueError, TypeError, KeyError):
            questions = 0
        
        # Get the list of option formsets, each one corresponds to a question
        
        option_formsets = [OptionFormSet(request.POST, \
            prefix='option' + str(i)) for i in range(questions)]
        
        # Get the question formset
        
        BaseQuestionFormSet1 = type(str('BaseQuestionFormSet'),
            (BaseQuestionFormSet,), dict(option_formsets=option_formsets))
        
        QuestionFormSet = PartialQuestionFormSet(formset=BaseQuestionFormSet1)
        question_formset = QuestionFormSet(request.POST, prefix='question')
        
        # Validate all forms
        
        election_valid = election_form.is_valid()
        question_valid = question_formset.is_valid()
        option_valid = all([formset.is_valid() for formset in option_formsets])
        
        if election_valid and question_valid and option_valid:
            
            election_obj = dict(election_form.cleaned_data)
            language = election_obj.pop('language')
            
            # Pack questions, options and trustees in lists of dictionaries
            
            election_obj['__list_Question__'] = []
            
            for q_index, (question_form, option_formset) \
                in enumerate(zip(question_formset, option_formsets)):
                
                question_obj = {
                    'index': q_index,
                    'text': question_form.cleaned_data['question'],
                    'columns': question_form.cleaned_data['columns'],
                    'choices': question_form.cleaned_data['choices'],
                    '__list_OptionC__': [],
                }
                
                for o_index, option_form in enumerate(option_formset):
                    
                    option_obj = {
                        'index': o_index,
                        'text': option_form.cleaned_data['text'],
                    }
                    
                    question_obj['__list_OptionC__'].append(option_obj)
                election_obj['__list_Question__'].append(question_obj)
            
            election_obj['__list_Trustee__'] = \
                [{'email': email} for email in election_obj.pop('trustee_list')]
            
            # Perform the requested action
            
            if request.is_ajax():
                
                q_options_list = [len(q_obj['__list_OptionC__'])
                    for q_obj in election_obj['__list_Question__']]
                
                vc_type = 'votecode' \
                    if not election_obj['long_votecodes'] else 'l_votecode'
                
                # Create a sample ballot. Since this is not a real ballot,
                # pseudo-random number generators are used instead of urandom.
                
                ballot_obj = {
                    'serial': 100,
                    '__list_Part__': [],
                }
                
                for p_index in ['A', 'B']:
                    
                    part_obj = {
                        'index': p_index,
                        'vote_token': 'vote_token',
                        'security_code': base32cf.random(
                            config.SECURITY_CODE_LEN, urandom=False),
                        '__list_Question__': [],
                    }
                    
                    for options in q_options_list:
                        
                        question_obj = {
                            '__list_OptionV__': [],
                        }
                        
                        if not election_obj['long_votecodes']:
                            votecode_list = list(range(1, options + 1))
                            random.shuffle(votecode_list)
                        else:
                            votecode_list=[base32cf.random(config.VOTECODE_LEN,
                                urandom=False) for _ in range(options)]
                        
                        for votecode in votecode_list:
                            
                            data_obj = {
                                vc_type: votecode,
                                'receipt': base32cf.random(
                                    config.RECEIPT_LEN, urandom=False),
                            }
                            
                            question_obj['__list_OptionV__'].append(data_obj)
                        part_obj['__list_Question__'].append(question_obj)
                    ballot_obj['__list_Part__'].append(part_obj)
                election_obj['id'] = 'election_id'
                
                # Temporarily enable the requested language
                
                translation.activate(language)
                
                builder = pdf.BallotBuilder(election_obj)
                pdfbuf = builder.pdfgen(ballot_obj)
                    
                translation.deactivate()
                
                # Return the pdf ballot as a base64 encoded string
                
                pdfb64 = b64encode(pdfbuf.getvalue())
                return http.HttpResponse(pdfb64.decode())
            
            else: # Create a new election
                
                with transaction.atomic():
                    
                    # Atomically get the next election id
                    
                    config_, created = Config.objects.select_for_update().\
                        get_or_create(key='next_election_id')
                    
                    election_id = config_.value if not created else '0'
                    next_election_id = base32cf.decode(election_id) + 1
                    
                    config_.value = base32cf.encode(next_election_id)
                    config_.save(update_fields=['value'])
                
                election_obj['id'] = election_id
                election_obj['state'] = enums.State.PENDING
                
                # Create the new election object
                
                election_kwargs = _prep_kwargs(election_obj, Election)
                election = Election.objects.create(**election_kwargs)
                
                # Prepare and start the election_setup task
                
                task = election_setup.s(election_obj, language)
                task.freeze()
                
                Task.objects.create(election=election, task_id=task.id)
                task.apply_async()
                
                # Redirect to status page
                
                return http.HttpResponseRedirect(urlresolvers.\
                    reverse('ea:status', args=[election_id]))
        
        # Add an empty question form and option formset
        
        question_and_options_list = list(zip(question_formset,
            option_formsets)) + [(question_formset.empty_form,
            OptionFormSet(prefix='option__prefix__'))]
        
        question_formset_errors = sum(int(not(question_form.is_valid() and \
            option_formset.is_valid())) for question_form, option_formset \
            in question_and_options_list[:-1])
        
        context = {
            'election_form': election_form,
            'question_formset': question_formset,
            'question_formset_errors': question_formset_errors,
            'question_and_options_list': question_and_options_list,
        }
        
        # Re-display the form with any errors
        return render(request, self.template_name, context, status=422)


class StatusView(View):
    
    template_name = 'ea/status.html'
    
    def get(self, request, *args, **kwargs):
        
        election_id = kwargs.get('election_id')
        
        normalized = base32cf.normalize(election_id)
        if normalized != election_id:
            return redirect('ea:status', election_id=normalized)
        
        try:
            election = Election.objects.get(id=election_id)
        except Election.DoesNotExist:
            election = None
        
        if not election:
           return redirect(reverse('ea:home') + '?error=id')
        
        abb_url = urljoin(config.URL['abb'], quote("results/%s/" % election_id))
        bds_url = urljoin(config.URL['bds'], quote("manage/%s/" % election_id))
        
        context = {
            'abb_url': abb_url,
            'bds_url': bds_url,
            'election': election,
            'State': {state.name: state.value for state in enums.State},
        }
        
        csrf.get_token(request)
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        
        election_id = kwargs.get('election_id')
        
        if election_id is None:
            return http.HttpResponseNotAllowed(['GET'])
        
        response = {}
        
        try: # Return election creation progress
            
            election = Election.objects.get(id=election_id)
            
            celery = Task.objects.get(election=election)
            task = AsyncResult(str(celery.task_id))
            
            response['state'] = enums.State.WORKING.value
            response.update(task.result or {})
        
        except Task.DoesNotExist:
            
            # Return election state or invalid
            
            if election.state.value == enums.State.RUNNING.value:
                if timezone.now() < election.start_datetime:
                    response['not_started'] = True
                elif timezone.now() > election.end_datetime:
                    response['ended'] = True
            
            response['state'] = election.state.value        
        
        except (ValidationError, Election.DoesNotExist):
            return http.HttpResponse(status=422)
        
        return http.JsonResponse(response)


class CryptoToolsView(View):
    
    @method_decorator(api.user_required('abb'))
    def dispatch(self, *args, **kwargs):
        return super(CryptoToolsView, self).dispatch(*args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        csrf.get_token(request)
        return http.HttpResponse()
    
    @staticmethod
    def _deserialize(field, cls):
        
        # Deserialize base64-encoded pb message
        
        field = field.encode('ascii')
        field = b64decode(field)
        
        pb_field = cls()
        pb_field.ParseFromString(field)
        
        return pb_field
    
    def post(self, request, *args, **kwargs):
        
        try:
            command = kwargs.pop('command')
            request_obj = json.loads(request.POST['data'])
            
            # Get common request data
            
            e_id = request_obj['e_id']
            q_index = request_obj['q_index']
            
            key = self._deserialize(request_obj['key'], crypto.Key)
            
            # Perform the requested action
            
            if command == 'add_com':
                
                # Input is a list of base64-encoded 'com' fields, returns 'com'.
                
                com_list = [self._deserialize(com, crypto.Com) \
                    for com in request_obj['com_list']]
                
                response = cryptotools.add_com(key, com_list)
            
            elif command == 'add_decom':
                
                # Input is a list of 3-tuples: (b_serial, p_index, o_index_list)
                # returns 'decom'.
                
                ballots = request_obj['ballots']
                
                if len(ballots) == 0:
                    
                    decom = crypto.Decom()
                    for _ in range(request_obj['options']):
                        dp = decom.dp.add()
                        dp.randomness = ''
                        dp.msg = 0
                
                for lo in range(0, len(ballots), config.BATCH_SIZE):
                    hi = lo + min(config.BATCH_SIZE, len(ballots) - lo)
                    
                    decom_list = [] if lo == 0 else [decom]
                    
                    for b_serial, p_index, o_index_list in ballots[lo: hi]:
                        
                        _decom_list = OptionV.objects.filter(
                            part__ballot__election__id=e_id,
                            part__ballot__serial=b_serial,
                            part__index=p_index,
                            question__index=q_index,
                            index__in=o_index_list,
                        ).values_list('decom', flat=True)
                        
                        decom_list.extend(_decom_list)
                    
                    decom = cryptotools.add_decom(key, decom_list)
                
                response = decom
                
            elif command == 'complete_zk':
                
                # Input is a list of 3-tuples: (b_serial, p_index, zk1_list),
                # where zk1_list is the list of all zk1 fields of this ballot
                # part, in ascending index order. Returns a list of zk2 lists,
                # in the same order.
                
                response = []
                
                coins = request_obj['coins']
                ballots = request_obj['ballots']
                
                options = OptionC.objects.filter(question__election__id=e_id, \
                    question__index=q_index).count()
                
                for b_serial, p_index, zk1_list in ballots:
                    
                    zk1_list = [self._deserialize(zk1, crypto.ZK1) \
                        for zk1 in zk1_list]
                    
                    zk_state_list = OptionV.objects.filter(part__index=\
                        p_index, part__ballot__serial=b_serial).\
                        values_list('zk_state', flat=True)
                    
                    zk_list = list(zip(zk1_list, zk_state_list))
                    zk2_list=cryptotools.complete_zk(key,options,coins,zk_list)
                    
                    response.append(zk2_list)
                
            elif command == 'verify_com':
                
                # Input is a 'com' and a 'decom' field, returns true or false
                
                com = self._deserialize(request_obj['com'], crypto.Com)
                decom = self._deserialize(request_obj['decom'], crypto.Decom)
                
                response = bool(cryptotools.verify_com(key, com, decom))
            
        except Exception:
            logger.exception('CryptoToolsView: API error')
            return http.HttpResponse(status=422)
        
        return http.JsonResponse(response,safe=False, encoder=CustomJSONEncoder)


class UpdateStateView(View):
    
    @method_decorator(api.user_required(['abb', 'vbb', 'bds']))
    def dispatch(self, *args, **kwargs):
        return super(UpdateStateView, self).dispatch(*args, **kwargs)
    
    def get(self, request):
        csrf.get_token(request)
        return http.HttpResponse()
    
    def post(self, request, *args, **kwargs):
        
        try:
            data = json.loads(request.POST['data'])
            
            e_id = data['e_id']
            election = Election.objects.get(id=e_id)
            
            state = enums.State(int(data['state']))
            
            # All servers can set state to ERROR, except for abb which can
            # also set it to COMPLETED, only if the election has ended.
            
            username = request.user.get_username()
            
            if not (state == enums.State.ERROR or (username == 'abb' \
                and state == enums.State.COMPLETED \
                and election.state == enums.State.RUNNING \
                and timezone.now() > election.end_datetime)):
                
                raise Exception('User \'%s\' tried to set election state to '
                    '\'%s\', but current state is \'%s\'.' \
                    % (username, state.name, election.state.name))
            
            # Update election state
            
            election.state = state
            election.save(update_fields=['state'])
            
            data = {
                'model': 'Election',
                'natural_key': {
                    'e_id': e_id
                },
                'fields': {
                    'state': state
                },
            }
            
            api_session = {app_name: api.Session(app_name, app_config)
                for app_name in ['abb','vbb','bds'] if not app_name == username}
            
            for app_name in api_session.keys():
                api_update(app_name, data=data, api_session=api_session, \
                    url_path='manage/update/');
            
        except Exception:
            logger.exception('UpdateStateView: API error')
            return http.HttpResponse(status=422)
        
        return http.HttpResponse()


class CenterView(View):
    
    template_name = 'ea/center.html'
    
    def get(self, request):
                # FIXME!
                return http.HttpResponse(status=404)

#eof
