# File: forms.py

from django import forms
from django.utils import timezone
from django.forms.formsets import BaseFormSet, formset_factory
from django.utils.translation import ugettext_lazy as _

from demos_ea.fields import MultiEmailField
from demos_utils.settings import *


def _trim_whitespace(field):
	
	# Helper function that removes all whitespace from a string
	
	field = " ".join(field.split())
	
	if not field:
		raise forms.ValidationError(
			forms.Field.default_error_messages['required'], code='required')
	
	return field


# DefineView Forms -------------------------------------------------------------

class ElectionForm(forms.Form):
	
	title = forms.CharField(label=_('Title'),
		min_length=1, max_length=TEXT_LEN)
	
	start_datetime = forms.DateTimeField(label=_('Start at'),
		input_formats=[DATETIME_FORMAT])
	
	end_datetime = forms.DateTimeField(label=_('End at'),
		input_formats=[DATETIME_FORMAT])
	
	ballots = forms.IntegerField(label=_('Ballots'),
		min_value=1, max_value=BALLOTS_MAX)
	
	trustees = MultiEmailField(label=_('Trustee e-mails'),
		min_length=1, max_length=TRUSTEES_MAX)
	
	language = forms.ChoiceField(label=_('Language'),
		choices=LANGUAGES)
	
	def clean_title(self):
		return _trim_whitespace(self.cleaned_data['title']);
	
	def clean_start_datetime(self):
		
		start_datetime = self.cleaned_data['start_datetime']
		
		# Verify start_datetime is valid
		
		if start_datetime < timezone.now():
			raise forms.ValidationError(
				_("Ensure start time is not in the past."), code='invalid')
		
		return start_datetime
	
	def clean_end_datetime(self):
		
		end_datetime = self.cleaned_data['end_datetime']
		
		# Verify end_datetime is valid
		
		if end_datetime < timezone.now():
			raise forms.ValidationError(
				_("Ensure end time is not in the past."), code='invalid')
		
		return end_datetime
	
	def clean(self):
		
		cleaned_data = super().clean()
		
		start_datetime = cleaned_data.get('start_datetime')
		end_datetime = cleaned_data.get('end_datetime')
		
		# Verify start_datetime is before end_datetime
		
		if start_datetime and end_datetime and end_datetime <= start_datetime:
			
			self.add_error(None, forms.ValidationError(
				_("Ensure start time is before end time."), code='required'))


class QuestionForm(forms.Form):
	
	question = forms.CharField(label=_('Question'),
		min_length=1, max_length=TEXT_LEN)
	
	two_columns = forms.BooleanField(label=_('Two columns'), required=False)
	
	def clean_question(self):
		return _trim_whitespace(self.cleaned_data['question']);
	
	def clean(self):
		
		cleaned_data = super().clean()
		two_columns = cleaned_data.get('two_columns')
		
		if not two_columns:
			cleaned_data['two_columns'] = False


class BaseQuestionFormSet(BaseFormSet):
	
	def clean(self):
		'''Checks that no two questions are the same.'''
		
		if any(self.errors):
			return
		
		question_list = []
		
		for form in self.forms:
			
			question = form.cleaned_data.get('question')
			
			if not question:
				form.add_error('question', forms.ValidationError(
					forms.Field.default_error_messages['required'],
					code='required'))
			
			else:
				if question in question_list:
					form.add_error(None, forms.ValidationError(
						_('Question already exists.'), code='not_unique'))
				else:
					question_list.append(question)


QuestionFormSet = formset_factory(QuestionForm, formset=BaseQuestionFormSet,
	min_num=1, max_num=QUESTIONS_MAX, validate_min=True,
	validate_max=True, extra=-1)


class OptionForm(forms.Form):
	
	option = forms.CharField(label=_('Option'),
		min_length=1, max_length=TEXT_LEN)
	
	def clean_option(self):
		return _trim_whitespace(self.cleaned_data['option']);


class BaseOptionFormSet(BaseFormSet):
	
	def clean(self):
		'''Checks that no two options are the same.'''
		
		if any(self.errors):
			return
		
		option_list = []
		
		for form in self.forms:
			
			option = form.cleaned_data.get('option')
			
			if not option:
				form.add_error('option', forms.ValidationError(
					forms.Field.default_error_messages['required'],
					code='required'))
			
			else:
				if option in option_list:
					form.add_error(None, forms.ValidationError(
						_('Option already exists.'), code='not_unique'))
				else:
					option_list.append(option)


OptionFormSet = formset_factory(OptionForm, formset=BaseOptionFormSet,
	min_num=2, max_num=OPTIONS_MAX, validate_min=True,
	validate_max=True, extra=0)


# ManageView Forms -------------------------------------------------------------

class ProgressForm(forms.Form):
	
	election_id = forms.CharField(min_length=1, max_length=8)

