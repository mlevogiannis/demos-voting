# File: views.py

from __future__ import absolute_import, division, print_function, unicode_literals

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

from demos_voting.apps.ea.forms import ElectionForm, OptionFormSet, PartialQuestionFormSet, BaseQuestionFormSet
from demos_voting.apps.ea.models import Conf, Election, Question, OptionV, Task
from demos_voting.apps.ea.tasks import election_setup, pdf
from demos_voting.apps.ea.tasks.setup import _remote_app_update
from demos_voting.common.utils import api, base32, enums
from demos_voting.common.utils.json import CustomJSONEncoder

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
                    'options_cnt': len(option_formset),
                    'choices': question_form.cleaned_data['choices'] \
                        if election_obj['type'] == Election.TYPE_REFERENDUM \
                        else min(len(option_formset), election_obj['choices']),
                    'columns': question_form.cleaned_data['columns'] \
                        if election_obj['type'] == Election.TYPE_REFERENDUM \
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
                    
                    conf = Conf.objects.get_or_create(**Conf.defaults())
                    
                    defaults = {f.name: election_obj[f.name] for f in
                        Election._meta.get_fields() if f.name in election_obj}
                    
                    election = Election.objects.select_for_update().create(id='-', conf=conf, **defaults)
                    election.full_clean(exclude=['id'])
                    
                    max_id = Election.objects.exclude(id=election.id).aggregate(Max('id'))['id__max']
                    election_id = '0' if max_id is None else base32.encode(base32.decode(max_id) + 1)
                    
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
        
        normalized = base32.normalize(election_id)
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

