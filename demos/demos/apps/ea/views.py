# File: views.py

from __future__ import absolute_import, division, unicode_literals

import logging
import random

from base64 import b64encode, b64decode

from django import http
from django.apps import apps
from django.core import urlresolvers
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Max
from django.middleware import csrf
from django.shortcuts import render, redirect
from django.utils import timezone, translation
from django.utils.decorators import method_decorator
from django.utils.six.moves import range, zip
from django.utils.six.moves.urllib.parse import quote, urljoin
from django.views.generic import View

from celery.result import AsyncResult

from demos.apps.ea.forms import ElectionForm, OptionFormSet, PartialQuestionFormSet, BaseQuestionFormSet
from demos.apps.ea.models import Election, Question, OptionV, Task
from demos.apps.ea.tasks import cryptotools, election_setup, pdf
from demos.apps.ea.tasks.setup import _remote_app_update
from demos.common.utils import api, base32cf, crypto, enums
from demos.common.utils.json import CustomJSONEncoder

logger = logging.getLogger(__name__)

app_config = apps.get_app_config('ea')
conf = app_config.get_constants_and_settings()


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
        
        question_and_options_list = [
            (question_formset.empty_form, OptionFormSet(prefix='option__prefix__'))
        ]
        
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
            if questions < 1 or questions > conf.MAX_QUESTIONS:
                raise ValueError
        except (ValueError, TypeError, KeyError):
            questions = 0
        
        # Get the list of option formsets, each one corresponds to a question
        
        option_formsets = [
            OptionFormSet(request.POST, prefix='option%s' % i) for i in range(questions)
        ]
        
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
                    'option_cnt': len(option_formset),
                    'choices': question_form.cleaned_data['choices'] \
                        if election_obj['type'] == enums.Type.REFERENDUM \
                        else min(len(option_formset), election_obj['choices']),
                    'columns': question_form.cleaned_data['columns'] \
                        if election_obj['type'] == enums.Type.REFERENDUM \
                        else False,
                    '__list_OptionC__': [],
                }
                
                for o_index, option_form in enumerate(option_formset):
                    
                    option_obj = {
                        'index': o_index,
                        'text': option_form.cleaned_data['text'],
                    }
                    
                    question_obj['__list_OptionC__'].append(option_obj)
                election_obj['__list_Question__'].append(question_obj)
            
            election_obj['__list_Trustee__'] = [
                {'email': email} for email in election_obj.pop('trustee_list')
            ]
            
            # Perform the requested action
            
            if request.is_ajax():
                
                # Create a sample ballot
                
                election_obj['id'] = 'election_id'
                
                # Temporarily enable the requested language
                
                translation.activate(language)
                
                pdfcreator = pdf.BallotPDFCreator(election_obj)
                pdfbuf = pdfcreator.sample()
                    
                translation.deactivate()
                
                # Return the pdf ballot as a base64 encoded string
                
                pdf_base64 = b64encode(pdfbuf.getvalue()).decode()
                return http.HttpResponse(pdf_base64)
            
            else:
                
                # Create a new election
                
                election_obj['state'] = enums.State.PENDING
                
                # Get the next election_id. Concurrency control is achieved by
                # locking for write an object with a predetermined, invalid ID.
                
                with transaction.atomic():
                    
                    defaults = {f.name: election_obj[f.name] for f in
                        Election._meta.get_fields() if f.name in election_obj}
                    
                    election = Election.objects.select_for_update().create(id='-', **defaults)
                    election.full_clean(exclude=['id'])
                    
                    max_id = Election.objects.exclude(id=election.id).aggregate(Max('id'))['id__max']
                    election_id = '0' if max_id is None else base32cf.encode(base32cf.decode(max_id) + 1)
                    
                    election.id = election_id
                    election.save(update_fields=['id'])
                
                election_obj['id'] = election_id
                
                # Prepare and start the election_setup task
                
                task = election_setup.s(election_obj, language)
                task.freeze()
                
                Task.objects.create(election=election, task_id=task.id)
                task.apply_async()
                
                # Redirect to status page
                
                return http.HttpResponseRedirect(
                    urlresolvers.reverse('ea:status', args=[election_id]))
        
        # Add an empty question form and option formset
        
        question_and_options_list = list(zip(question_formset,
            option_formsets)) + [(question_formset.empty_form,
            OptionFormSet(prefix='option__prefix__'))]
        
        question_formset_errors = sum(int(not(question_form.is_valid() and
            option_formset.is_valid())) for question_form, option_formset
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
        
        abb_url = urljoin(conf.URL['abb'], quote("results/%s/" % election_id))
        bds_url = urljoin(conf.URL['bds'], quote("manage/%s/" % election_id))
        
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
                if timezone.now() < election.starts_at:
                    response['not_started'] = True
                elif timezone.now() > election.ends_at:
                    response['ended'] = True
            
            response['state'] = election.state.value        
        
        except (ValidationError, Election.DoesNotExist):
            return http.HttpResponse(status=422)
        
        return http.JsonResponse(response)


class CenterView(View):
    
    template_name = 'ea/center.html'
    
    def get(self, request):
        # FIXME!
        return http.HttpResponse(status=404)


# API Views --------------------------------------------------------------------

class ApiCryptoView(View):
    
    @method_decorator(api.user_required('abb'))
    def dispatch(self, *args, **kwargs):
        return super(ApiCryptoView, self).dispatch(*args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        csrf.get_token(request)
        return http.HttpResponse()
    
    @staticmethod
    def _deserialize(field_or_list, pb_cls):
        
        is_field = not isinstance(field_or_list, (list, tuple))
        field_list = [ field_or_list ] if is_field else field_or_list
        
        # Deserialize a list of base64-encoded pb messages
        
        pb_field_list = []
        
        for field in field_list:
            
            field = field.encode('ascii')
            field = b64decode(field)
            
            pb_field = pb_cls()
            pb_field.ParseFromString(field)
            
            pb_field_list.append(pb_field)
        
        return pb_field_list[0] if is_field else pb_field_list
    
    def post(self, request, *args, **kwargs):
        
        try:
            command = kwargs.pop('command')
            request_obj = api.ApiSession.load_json_request(request.POST)
            
            # Get common request data
            
            e_id = request_obj['e_id']
            q_index = request_obj['q_index']
            
            key = self._deserialize(request_obj['key'], crypto.Key)
            
            # Perform the requested action
            
            if command == 'add_com':
                
                # Input is a list of base64-encoded 'com' fields, returns 'com'
                
                com_list = self._deserialize(request_obj['com_list'], crypto.Com)
                
                # Add 'com' fields
                
                for lo in range(0, len(com_list), conf.BATCH_SIZE):
                    hi = lo + min(conf.BATCH_SIZE, len(com_list) - lo)
                    
                    com_buf = com_list[lo: hi]
                    
                    if lo > 0:
                        com_buf.append(com)
                    
                    com = cryptotools.add_com(key, com_buf)
                
                # Special case: no ballots
                
                if len(com_list) == 0:
                    com = cryptotools.add_com(key, [])
                
                response = com
                
            elif command == 'add_decom':
                
                # Input is a list of 3-tuples: (b_serial, p_index,
                # o_index_list), returns 'decom'
                
                ballots = request_obj['ballots']
                
                # Add 'decom' fields
                
                decom_buf = []
                
                for b_serial, p_index, o_index_list in ballots:
                    
                    optionv_qs = OptionV.objects.filter(
                        part__ballot__election__id=e_id, part__ballot__serial=
                        b_serial, question__index=q_index, part__index=p_index
                    )
                    
                    for lo in range(0, len(o_index_list), conf.BATCH_SIZE):
                        hi = lo + min(conf.BATCH_SIZE, len(o_index_list) - lo)
                        
                        _qs = optionv_qs.filter(index__in=o_index_list[lo:hi])
                        decom_buf.extend(_qs.values_list('decom', flat=True))
                        
                        # Flush the buffer
                        
                        if len(decom_buf) > conf.BATCH_SIZE:
                            
                            decom = cryptotools.add_decom(key, decom_buf)
                            decom_buf = [ decom ]
                
                # Return the combined decom (len = 1), flush the non-empty
                # buffer (len > 1), or add the empty list (len = 0, generates
                # an empty decom)
                
                response = decom_buf[0] if len(decom_buf) == 1 \
                    else cryptotools.add_decom(key, decom_buf)
                
            elif command == 'complete_zk':
                
                # Input is a list of 3-tuples: (b_serial, p_index, o_iz_list),
                # where o_iz_list is the list of 2-tuples: (o_index, zk1).
                # Returns a list of zk2 lists, in the same order.
                
                coins = request_obj['coins']
                ballots = request_obj['ballots']
                
                option_cnt = Question.objects.only('option_cnt').\
                    get(index=q_index, election__id=e_id).option_cnt
                
                # Compute 'zk2' fields
                
                zk_buf = []
                zk2_list = []
                
                for b_serial, p_index, o_iz_list in ballots:
                    
                    optionv_qs = OptionV.objects.filter(
                        part__index=p_index, part__ballot__serial=b_serial
                    )
                    
                    for lo in range(0, len(o_iz_list), conf.BATCH_SIZE):
                        hi = lo + min(conf.BATCH_SIZE, len(o_iz_list) - lo)
                        
                        o_index_list, zk1_list = zip(*o_iz_list)
                        zk1_list = self._deserialize(zk1_list, crypto.ZK1)
                        
                        _qs = optionv_qs.filter(index__in=o_index_list[lo:hi])
                        zk_state_list = _qs.values_list('zk_state', flat=True)
                        
                        zk_buf.extend(zip(zk1_list, zk_state_list))
                        
                        # Flush the buffer
                        
                        if len(zk_buf) > conf.BATCH_SIZE:
                            
                            zk2_list.extend(cryptotools.complete_zk(key, option_cnt, coins, zk_buf))
                            zk_buf = []
                
                # Flush non-empty buffer
                
                if zk_buf:
                    zk2_list.extend(cryptotools.complete_zk(key, option_cnt, coins, zk_buf))
                
                # Re-create input's structure
                
                lo = hi = 0
                response = []
                
                for _, _, o_iz_list in ballots:
                    
                    lo = hi
                    hi = lo + len(o_iz_list)
                    
                    response.append(zk2_list[lo: hi])
                
            elif command == 'verify_com':
                
                # Input is a 'com' and a 'decom' field, returns true or false
                
                com = self._deserialize(request_obj['com'], crypto.Com)
                decom = self._deserialize(request_obj['decom'], crypto.Decom)
                
                response = bool(cryptotools.verify_com(key, com, decom))
            
        except Exception:
            logger.exception('CryptoToolsView: API error')
            return http.HttpResponse(status=422)
        
        return http.JsonResponse(response, safe=False, encoder=CustomJSONEncoder)


class ApiUpdateStateView(View):
    
    @method_decorator(api.user_required(['abb', 'vbb', 'bds']))
    def dispatch(self, *args, **kwargs):
        return super(ApiUpdateStateView, self).dispatch(*args, **kwargs)
    
    def get(self, request):
        
        csrf.get_token(request)
        return http.HttpResponse()
    
    def post(self, request, *args, **kwargs):
        
        try:
            data = api.ApiSession.load_json_request(request.POST)
            
            e_id = data['e_id']
            election = Election.objects.get(id=e_id)
            
            state = enums.State(int(data['state']))
            
            # All servers can set state to ERROR, except for abb which can
            # also set it to COMPLETED, only if the election has ended.
            
            username = request.user.get_username()
            
            if not (state == enums.State.ERROR or (username == 'abb' \
                and state == enums.State.COMPLETED \
                and election.state == enums.State.RUNNING \
                and timezone.now() > election.ends_at)):
                
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
            
            api_session = {app_name: api.ApiSession(app_name, app_config)
                for app_name in ['abb','vbb','bds'] if not app_name == username}
            
            for app_name in api_session.keys():
                _remote_app_update(app_name, data=data, \
                    api_session=api_session, url_path='api/update/');
            
        except Exception:
            logger.exception('UpdateStateView: API error')
            return http.HttpResponse(status=422)
        
        return http.HttpResponse()

