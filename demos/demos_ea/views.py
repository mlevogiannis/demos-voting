# File: views.py

from django.db import transaction
from django.core import urlresolvers
from django.shortcuts import render
from django.views.generic import View
from django.http import (
	HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, JsonResponse
)

from celery.result import AsyncResult

from demos_ea.tasks import election_setup
from demos_ea.models import Config, Election, Task
from demos_ea.forms import (
	ElectionForm, QuestionFormSet, OptionFormSet, ProgressForm
)

from demos_utils.enums import State
from demos_utils.base32cf import b32cf_encode, b32cf_decode
from demos_utils.settings import *


class HomeView(View):
	
	template = 'demos_ea/home.html'
	
	def get(self, request):
		return render(request, self.template, {})


class DefineView(View):
	
	template = 'demos_ea/define.html'
	
	def get(self, request, *args, **kwargs):
		
		election_form = ElectionForm(prefix='election')
		question_formset = QuestionFormSet(prefix='question')
		
		question_formset_incl_options = [(question_formset.empty_form,
			OptionFormSet(prefix='option__prefix__'))]
		
		context = {
			'election_form': election_form,
			'question_formset': question_formset,
			'question_formset_incl_options': question_formset_incl_options,
			'datetime_format': DATETIME_FORMAT_JS,
		}
		
		return render(request, self.template, context)

	def post(self, request, *args, **kwargs):
		
		# Parse POST forms
		
		election_form = ElectionForm(request.POST, prefix='election')
		question_formset = QuestionFormSet(request.POST, prefix='question')
		
		question_formset_incl_options = [(question_form,
			OptionFormSet(request.POST, prefix='option' + str(i)))
			for i, question_form in enumerate(question_formset)]
		
		# Validate all forms
		
		election_valid = election_form.is_valid()
		question_valid = question_formset.is_valid()
		
		option_valid = all([option_formset.is_valid() for _, option_formset
			in question_formset_incl_options])
		
		if election_valid and question_valid and option_valid:
			
			# Get election cleaned data
			
			title = election_form.cleaned_data['title']
			
			start_datetime = election_form.cleaned_data['start_datetime']
			end_datetime = election_form.cleaned_data['end_datetime']
			
			ballots = election_form.cleaned_data['ballots']
			language = election_form.cleaned_data['language']
			
			trustee_list = election_form.cleaned_data['trustees']
			
			# Get question cleaned data
			
			question_list = []
			
			for question_form, option_formset in question_formset_incl_options:
				
				question = question_form.cleaned_data['question']
				two_columns = question_form.cleaned_data['two_columns']
				
				option_list = [option_form.cleaned_data['option']
					for option_form in option_formset]
				
				question_list.append((question, two_columns, option_list))
			
			# Atomically get the next available election id
			
			with transaction.atomic():
				
				config, created = Config.objects.select_for_update().\
					get_or_create(option_name='next_election_id')
				
				election_id = config.option_value if not created else '0'
				
				config.option_value = b32cf_encode(b32cf_decode(election_id)+1)
				config.save(update_fields=['option_value'])
			
			# Prepare and start the election_setup task
			
			task = election_setup.s(election_id, title, start_datetime,
				end_datetime, ballots, language, trustee_list, question_list)
			task.freeze()
			
			Task.objects.create(election_id=election_id, task_id=task.id)
			task.apply_async()
			
			# Redirect to manage page
			
			return HttpResponseRedirect(urlresolvers.reverse('demos_ea:manage',
				args=[election_id]))
		
		# Add the empty question form
		
		question_formset_incl_options += [(question_formset.empty_form,
			OptionFormSet(prefix='option__prefix__'))]
		
		context = {
			'election_form': election_form,
			'question_formset': question_formset,
			'question_formset_incl_options': question_formset_incl_options,
			'datetime_format': DATETIME_FORMAT_JS,
		}
		
		# Re-desplay the form with any errors
		
		return render(request, self.template, context)


class ManageView(View):
	
	template = 'demos_ea/manage.html'
	
	def get(self, request, election_id):
		
		context = {
			'election_id': election_id,
			'state': {state.name: state.value for state in State}
		}
		
		return render(request, self.template, context)
	
	def post(self, request, *args, **kwargs):
		
		progress_form = ProgressForm(request.POST)
		
		# Check if the post request is valid
		
		if progress_form.is_valid() and request.is_ajax():
			
			response = {}
			election_id = progress_form.cleaned_data['election_id']
			
			try: # Return election creation progress
				
				celery = Task.objects.get(election_id=election_id)
				task = AsyncResult(str(celery.task_id))
				
				response['state'] = State.WORKING.value
				response.update(task.result or {'current': 0, 'total': 1})
			
			except: # Return election state or invalid
				
				try:
					election = Election.objects.get(election_id=election_id)
					response['state'] = election.state.value
				
				except:
					response['state'] = State.INVALID.value
			
			return JsonResponse(response)
		
		return HttpResponseBadRequest()

