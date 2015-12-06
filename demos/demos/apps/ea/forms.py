# File: forms.py

from __future__ import absolute_import, division, unicode_literals

from functools import partial

from django import forms
from django.apps import apps
from django.conf import settings
from django.forms.formsets import BaseFormSet, formset_factory
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from demos.common.utils import enums, fields

app_config = apps.get_app_config('ea')
conf = app_config.get_constants_and_settings()


class ElectionForm(forms.Form):
    
    name = forms.CharField(label=_('Name'),
        min_length=1, max_length=conf.ELECTION_MAXLEN)
    
    starts_at = fields.DateTimeField(label=_('Start at'))
    ends_at = fields.DateTimeField(label=_('End at'))
    
    ballot_cnt = forms.IntegerField(label=_('Ballots'),
        min_value=1, max_value=conf.MAX_BALLOTS)
    
    language = forms.ChoiceField(label=_('Language'),
        choices=settings.LANGUAGES)
    
    trustee_list = fields.MultiEmailField(label=_('Trustee e-mails'),
        min_length=1, max_length=conf.MAX_TRUSTEES, required=False)
    
    _votecode_type_choices = (
        ('short', _('Short')),
        ('long', _('Long'))
    )
    
    votecode_type = forms.ChoiceField(label=_('Vote-codes'),
        choices=_votecode_type_choices)
    
    _election_type_choices = (
        ('elections', _('Elections')),
        ('referendum', _('Referendum'))
    )
    
    election_type = forms.ChoiceField(label=_('Election type'),
        choices=_election_type_choices)
    
    _election_system_choices = (
        ('pr',  _('Proportional representation')),
        ('mbs', _('Majority bonus system')),
        ('mmp', _('Mixed Member Proportional')),
        ('mr',  _('Majority rule')),
    )
    
    electoral_system = forms.ChoiceField(label=_('Electoral system'),
        choices=_election_system_choices, required=False)
    
    choices = forms.IntegerField(label=_('Choices'),
        initial=1, min_value=1, max_value=conf.MAX_OPTIONS, required=False)
    
    error_msg = {
        'passed': _("The date and time you selected have passed."),
        'order': _("Start and end dates and times are not in logical order.")
    }
    
    def clean_name(self):
        return _trim_whitespace(self.cleaned_data['name']);
    
    def clean_starts_at(self):
        
        starts_at = self.cleaned_data['starts_at']
        
        # Verify that starts_at is valid
        
        if starts_at < timezone.now():
            raise forms.ValidationError(self.error_msg['passed'],code='invalid')
        
        return starts_at
    
    def clean_ends_at(self):
        
        ends_at = self.cleaned_data['ends_at']
        
        # Verify that ends_at is valid
        
        if ends_at < timezone.now():
            raise forms.ValidationError(self.error_msg['passed'],code='invalid')
        
        return ends_at
    
    def clean(self):
        
        cleaned_data = super(ElectionForm, self).clean()
        
        # Verify that ends_at is not before starts_at
        
        starts_at = cleaned_data.get('starts_at')
        ends_at = cleaned_data.get('ends_at')
        
        if starts_at and ends_at and ends_at <= starts_at:
            error=forms.ValidationError(self.error_msg['order'], code='invalid')
            self.add_error(None, error)
        
        # 'vc_type' depends on 'votecode_type'
        
        votecode_type = cleaned_data.get('votecode_type')
        
        if votecode_type is not None:
            
            if votecode_type == 'short':
                cleaned_data['vc_type'] = enums.VcType.SHORT
            elif votecode_type == 'long':
                cleaned_data['vc_type'] = enums.VcType.LONG
        
        # 'type' depends on 'election_type'
        
        election_type = cleaned_data.get('election_type')
        
        if election_type is not None:
            
            if election_type == 'elections':
                cleaned_data['type'] = enums.Type.ELECTIONS
            elif election_type == 'referendum':
                cleaned_data['type'] = enums.Type.REFERENDUM
        
        # 'electoral_system' and 'choices' are required if and only if
        # 'election_type' is 'elections'
        
        if cleaned_data.get('type') == enums.Type.ELECTIONS:
            
            for field in ('electoral_system', 'choices'):
                if not cleaned_data.get(field):
                    self.add_error(field, forms.ValidationError(forms.Field.\
                        default_error_messages['required'], code='required'))


class QuestionForm(forms.Form):
    
    question = forms.CharField(label=_('Question'), min_length=1,
        max_length=conf.QUESTION_MAXLEN)
    
    columns = forms.BooleanField(label=_('Display in columns'), required=False)
    
    def __init__(self, *args, **kwargs):
        
        option_formset = kwargs.pop('option_formset', None)
        choices = option_formset.total_form_count() if option_formset else 2
        
        super(QuestionForm, self).__init__(*args, **kwargs)
        
        self.fields['choices'] = forms.IntegerField(label=_('Multiple choices'),
            initial=1, min_value=1, max_value=choices)
    
    def clean_question(self):
        return _trim_whitespace(self.cleaned_data['question']);


class BaseQuestionFormSet(BaseFormSet):
    
    def __init__(self, *args, **kwargs):
        
        super(BaseQuestionFormSet, self).__init__(*args, **kwargs)
        
        for form in self.forms:
            form.empty_permitted = False
    
    def _construct_form(self, i, **kwargs):
        
        # Workaround for 'form_kwargs' not supported in Django 1.8.x
        # See https://code.djangoproject.com/ticket/18166
        
        kwargs['option_formset'] = self.option_formsets[i]
        return super(BaseQuestionFormSet, self)._construct_form(i, **kwargs)
    
    def clean(self):
        '''Checks that no two questions are the same.'''
        
        if any(self.errors):
            return
        
        question_list = []
        
        for form in self.forms:
            
            question = form.cleaned_data.get('question')
            
            if not question:
                form.add_error('question', forms.ValidationError(forms.\
                    Field.default_error_messages['required'], code='required'))
            
            else:
                if question in question_list:
                    form.add_error(None, forms.ValidationError(
                        _('Question already exists.'), code='not_unique'))
                else:
                    question_list.append(question)


class OptionForm(forms.Form):
    
    text = forms.CharField(label=_('Option'),
        min_length=1, max_length=conf.OPTION_MAXLEN)
    
    def clean_option(self):
        return _trim_whitespace(self.cleaned_data['text']);


class BaseOptionFormSet(BaseFormSet):
    
    def __init__(self, *args, **kwargs):
        super(BaseOptionFormSet, self).__init__(*args, **kwargs)
        for form in self.forms:
            form.empty_permitted = False
    
    def clean(self):
        '''Checks that no two options are the same.'''
        
        if any(self.errors):
            return
        
        text_list = []
        
        for form in self.forms:
            
            text = form.cleaned_data.get('text')
            
            if not text:
                form.add_error('text', forms.ValidationError(
                    forms.Field.default_error_messages['required'],
                    code='required'))
            
            else:
                if text in text_list:
                    form.add_error(None, forms.ValidationError(
                        _('Option already exists.'), code='not_unique'))
                else:
                    text_list.append(text)


PartialQuestionFormSet = partial(formset_factory, QuestionForm, extra=-1, 
    validate_min=True, validate_max=True, min_num=1, max_num=conf.MAX_QUESTIONS)

OptionFormSet = formset_factory(OptionForm, formset=BaseOptionFormSet, extra=0,
    validate_min=True, validate_max=True, min_num=2, max_num=conf.MAX_OPTIONS)

# ------------------------------------------------------------------------------

def _trim_whitespace(field):
    """Replace a string's continuous whitespace by a single space"""
    
    field = " ".join(field.split())
    
    if not field:
        raise forms.ValidationError(
            forms.Field.default_error_messages['required'], code='required')
    
    return field

