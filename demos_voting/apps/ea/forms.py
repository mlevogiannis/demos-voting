# File: forms.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django import forms
from django.conf import settings
from django.core import validators
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.six.moves import range, zip
from django.utils.translation import ugettext_lazy as _

from demos_voting.apps.ea.fields import ISO8601DateTimeField, MultiEmailField
from demos_voting.apps.ea.models import Election, Question, Option, Trustee


class ElectionForm(forms.ModelForm):

    trustee_emails = MultiEmailField(
        label=_("Trustee emails"),
        min_num=1,
        max_num=settings.DEMOS_VOTING_MAX_TRUSTEES
    )

    max_candidate_choices = forms.IntegerField(
        label=_("Maximum number of candidate choices"),
        required=False,
        min_value=1
    )

    # https://code.djangoproject.com/ticket/24295
    voting_starts_at = Election._meta.get_field('voting_starts_at').formfield(form_class=ISO8601DateTimeField)
    voting_ends_at = Election._meta.get_field('voting_ends_at').formfield(form_class=ISO8601DateTimeField)

    def __init__(self, *args, **kwargs):
        self.datetime_now = timezone.now()
        self.question_formset = kwargs.pop('question_formset', None)
        self.party_formset = kwargs.pop('party_formset', None)

        initial = kwargs.setdefault('initial', {})
        initial.setdefault('type', Election.TYPE_REFERENDUM)
        initial.setdefault('votecode_type', Election.VOTECODE_TYPE_SHORT)
        initial.setdefault('security_code_type', Election.SECURITY_CODE_TYPE_NUMERIC)

        self.type_election = Election.TYPE_ELECTION
        self.type_referendum = Election.TYPE_REFERENDUM

        super(ElectionForm, self).__init__(*args, **kwargs)
        self.fields['ballot_count'].min_value = 1

    def clean_name(self):
        name = self.cleaned_data['name']
        name = ' '.join(name.split())
        validators.MinLengthValidator(1)(name)
        validators.MaxLengthValidator(100)(name)
        return name

    def clean_voting_starts_at(self):
        voting_starts_at = self.cleaned_data['voting_starts_at']
        if voting_starts_at <= self.datetime_now:
            message = _("Ensure that voting start time is in the future.")
            raise forms.ValidationError(message, code='invalid')
        return voting_starts_at

    def clean_voting_ends_at(self):
        voting_ends_at = self.cleaned_data['voting_ends_at']
        if voting_ends_at <= self.datetime_now:
            message = _("Ensure that voting end time is in the future.")
            raise forms.ValidationError(message, code='invalid')
        return voting_ends_at

    def clean_ballot_count(self):
        ballot_count = self.cleaned_data['ballot_count']
        validators.MinValueValidator(1)(ballot_count)
        validators.MaxValueValidator(settings.DEMOS_VOTING_MAX_BALLOTS)(ballot_count)
        return ballot_count

    def clean(self):
        cleaned_data = super(ElectionForm, self).clean()

        voting_starts_at = cleaned_data.get('voting_starts_at')
        voting_ends_at = cleaned_data.get('voting_ends_at')
        if voting_starts_at and voting_ends_at and voting_starts_at > voting_ends_at:
            message = _("Ensure that voting start time is before voting end time.")
            self.add_error(None, forms.ValidationError(message, code='invalid'))

        type = cleaned_data.get('type')
        if type == Election.TYPE_ELECTION:
            max_candidate_choices = cleaned_data.get('max_candidate_choices')
            try:
                if max_candidate_choices is None:
                    raise forms.ValidationError(forms.Field.default_error_messages['required'], code='required')
                else:
                    validators.MinValueValidator(1)(max_candidate_choices)
                    if self.party_formset and self.party_formset.total_form_count() > 0 and all(
                        party_form.candidate_formset and party_form.candidate_formset.is_valid()
                        for party_form
                        in self.party_formset
                    ):
                        max_candidate_count = max(
                            party_form.candidate_formset.total_form_count()
                            for party_form
                            in self.party_formset
                        )
                        validators.MaxValueValidator(max_candidate_count)(max_candidate_choices)
            except forms.ValidationError as e:
                self.add_error('max_candidate_choices', e)

        votecode_type = cleaned_data.get('votecode_type')
        security_code_type = cleaned_data.get('security_code_type')
        if (votecode_type == Election.VOTECODE_TYPE_LONG
                and not security_code_type == Election.SECURITY_CODE_TYPE_ALPHANUMERIC):
            message = _("Vote-codes of type long require a security code of type alphanumeric.")
            self.add_error(None, forms.ValidationError(message, code='invalid'))

    class Meta:
        model = Election
        fields = [
            'name', 'voting_starts_at', 'voting_ends_at', 'type', 'votecode_type', 'security_code_type',
            'ballot_count', 'max_candidate_choices', 'trustee_emails'
        ]
        widgets = {
            'name': forms.TextInput,
            'type': forms.RadioSelect,
            'votecode_type': forms.RadioSelect,
            'security_code_type': forms.RadioSelect,
        }


class QuestionForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.option_formset = kwargs.pop('option_formset', None)
        super(QuestionForm, self).__init__(*args, **kwargs)
        self.fields['min_choices'].min_value = 1
        self.fields['max_choices'].min_value = 1

    def clean_name(self):
        name = self.cleaned_data['name']
        name = ' '.join(name.split())
        validators.MinLengthValidator(1)(name)
        validators.MaxLengthValidator(100)(name)
        return name

    def clean_min_choices(self):
        min_choices = self.cleaned_data['min_choices']
        validators.MinValueValidator(1)(min_choices)
        if self.option_formset and self.option_formset.is_valid():
            validators.MaxValueValidator(self.option_formset.total_form_count() - 1)(min_choices)
        return min_choices

    def clean_max_choices(self):
        max_choices = self.cleaned_data['max_choices']
        validators.MinValueValidator(1)(max_choices)
        if self.option_formset and self.option_formset.is_valid():
            validators.MaxValueValidator(self.option_formset.total_form_count())(max_choices)
        return max_choices

    def clean(self):
        cleaned_data = super(QuestionForm, self).clean()
        min_choices = cleaned_data.get('min_choices')
        max_choices = cleaned_data.get('max_choices')
        if min_choices and max_choices and  min_choices > max_choices:
            message = _("Ensure that the minimum number of choices is less than the maximum number of choices.")
            self.add_error(None, forms.ValidationError(message, code='invalid'))

    class Meta:
        model = Question
        fields = ['name', 'min_choices', 'max_choices', 'table_layout']
        widgets = {
            'name': forms.TextInput,
        }


class OptionForm(forms.ModelForm):

    def clean_name(self):
        name = self.cleaned_data['name']
        name = ' '.join(name.split())
        validators.MinLengthValidator(1)(name)
        validators.MaxLengthValidator(50)(name)
        return name

    class Meta:
        model = Option
        fields = ['name']
        widgets = {
            'name': forms.TextInput,
        }


class PartyForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.candidate_formset = kwargs.pop('candidate_formset', None)
        super(PartyForm, self).__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data['name']
        name = ' '.join(name.split())
        validators.MinLengthValidator(1)(name)
        validators.MaxLengthValidator(100)(name)
        return name

    class Meta:
        model = Option
        fields = ['name']
        widgets = {
            'name': forms.TextInput,
        }


class CandidateForm(forms.ModelForm):

    def clean_name(self):
        name = self.cleaned_data['name']
        name = ' '.join(name.split())
        validators.MinLengthValidator(1)(name)
        validators.MaxLengthValidator(50)(name)
        return name

    class Meta:
        model = Option
        fields = ['name']
        widgets = {
            'name': forms.TextInput,
        }

# -----------------------------------------------------------------------------

class FormKwargsMixin(object):

    # Backport from Django 1.9
    # Added ability to pass kwargs to the form constructor in a formset.
    # https://code.djangoproject.com/ticket/18166
    # https://github.com/django/django/commit/fe21fb810a1bd12b10c534923809423b5c1cf4d7

    def __init__(self, *args, **kwargs):
        self.form_kwargs = kwargs.pop('form_kwargs', {})
        super(FormKwargsMixin, self).__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        return self.form_kwargs.copy()

    @cached_property
    def forms(self):
        return [self._construct_form(i, **self.get_form_kwargs(i)) for i in range(self.total_form_count())]

    @property
    def empty_form(self):
        form = self.form(
            auto_id=self.auto_id,
            prefix=self.add_prefix('__prefix__'),
            empty_permitted=True,
            **self.get_form_kwargs(None)
        )
        self.add_fields(form, None)
        return form


class CommonMixin(object):

    def _construct_form(self, *args, **kwargs):
        form = super(CommonMixin, self)._construct_form(*args, **kwargs)
        form.empty_permitted = False
        return form

    def is_valid(self):
        try:
            is_valid = super(CommonMixin, self).is_valid()
        except forms.ValidationError as e:
            if e.code != 'missing_management_form':
                raise
            else:
                return False
        else:
            return is_valid

    def clean(self):
        super(CommonMixin, self).clean()
        if any(self.errors):
            return
        values = set()
        for form in self.forms:
            value = getattr(form.instance, self.form_validators['unique'])
            if value in values:
                raise forms.ValidationError(self.error_messages['unique'], code='unique')
            values.add(value)


class BaseQuestionFormSet(FormKwargsMixin, CommonMixin, forms.BaseInlineFormSet):

    form_validators = {
        'unique': 'name'
    }

    error_messages = {
        'unique': _("Ensure that questions have distinct names.")
    }

    def get_form_kwargs(self, index):
        kwargs = super(BaseQuestionFormSet, self).get_form_kwargs(index)
        option_formsets = kwargs.pop('option_formsets', None)
        if index is not None and option_formsets is not None:
            kwargs['option_formset'] = option_formsets[index]
        return kwargs


class BaseOptionFormSet(CommonMixin, forms.BaseInlineFormSet):

    form_validators = {
        'unique': 'name'
    }

    error_messages = {
        'unique': _("Ensure that options have distinct names.")
    }


class BasePartyFormSet(FormKwargsMixin, CommonMixin, forms.BaseModelFormSet):

    form_validators = {
        'unique': 'name'
    }

    error_messages = {
        'unique': _("Ensure that paties have distinct names.")
    }

    def get_form_kwargs(self, index):
        kwargs = super(BasePartyFormSet, self).get_form_kwargs(index)
        candidate_formsets = kwargs.pop('candidate_formsets', None)
        if index is not None and candidate_formsets is not None:
            kwargs['candidate_formset'] = candidate_formsets[index]
        return kwargs


class BaseCandidateFormSet(CommonMixin, forms.BaseModelFormSet):

    form_validators = {
        'unique': 'name'
    }

    error_messages = {
        'unique': _("Ensure that candidates have distinct names.")
    }


QuestionFormSet = forms.inlineformset_factory(
    parent_model=Election,
    model=Question,
    form=QuestionForm,
    formset=BaseQuestionFormSet,
    extra=-1,
    can_delete=False,
    validate_min=True,
    validate_max=True,
    min_num=1,
    max_num=settings.DEMOS_VOTING_MAX_REFERENDUM_QUESTIONS
)

OptionFormSet = forms.inlineformset_factory(
    parent_model=Question,
    model=Option,
    form=OptionForm,
    formset=BaseOptionFormSet,
    extra=-1,
    can_delete=False,
    validate_min=True,
    validate_max=True,
    min_num=2,
    max_num=settings.DEMOS_VOTING_MAX_REFERENDUM_OPTIONS
)

PartyFormSet = forms.modelformset_factory(
    model=Option,
    form=PartyForm,
    formset=BasePartyFormSet,
    extra=-1,
    validate_min=True,
    validate_max=True,
    min_num=1,
    max_num=settings.DEMOS_VOTING_MAX_ELECTION_PARTIES
)

CandidateFormSet = forms.modelformset_factory(
    model=Option,
    form=CandidateForm,
    formset=BaseCandidateFormSet,
    extra=-1,
    validate_min=True,
    validate_max=True,
    min_num=1,
    max_num=settings.DEMOS_VOTING_MAX_ELECTION_CANDIDATES
)

# -----------------------------------------------------------------------------

def create_trustees(election_form):

    election = election_form.save(commit=False)
    trustee_emails = election_form.cleaned_data['trustee_emails']

    return [Trustee(election=election, email=email) for email in trustee_emails]


def create_questions_and_options(election_form):

    election = election_form.save(commit=False)

    if election.type_is_election:

        party_formset = election_form.party_formset
        candidate_formsets = [party_form.candidate_formset for party_form in party_formset]

        max_candidate_choices = election_form.cleaned_data['max_candidate_choices']

        # An election with parties and candidates always has two questions, the
        # party list and the candidate list.

        party_question = Question(
            name=None,
            min_choices=1,
            max_choices=1,
            table_layout=Question.TABLE_LAYOUT_ONE_COLUMN
        )

        candidate_question = Question(
            name=None,
            min_choices=max_candidate_choices,
            max_choices=max_candidate_choices,
            table_layout=Question.TABLE_LAYOUT_ONE_COLUMN
        )

        # The first question is the party list. The last party is always the blank
        # party.

        party_options = party_formset.save(commit=False) + [Option(name=None)]

        # The second question is the candidate list. It has a special structure by
        # grouping together the options that correspond to each party's candidates.
        # All parties should always have the same number of candidates, which is
        # the maximum number of candidates plus the maximum number of choices. So,
        # parties with less candidates are padded with blank candidates. The blank
        # party has only blank candidates.

        max_candidate_count = max(formset.total_form_count() for formset in candidate_formsets) + max_candidate_choices

        candidate_options = []
        for formset in candidate_formsets + [CandidateFormSet(data={'form-TOTAL_FORMS': 0, 'form-INITIAL_FORMS': 0})]:
            candidate_options.extend(formset.save(commit=False))
            candidate_options.extend(Option(name=None) for _ in range(max_candidate_count-formset.total_form_count()))

        questions = [party_question, candidate_question]
        optionss = [party_options, candidate_options]

    elif election.type_is_referendum:

        question_formset = election_form.question_formset
        option_formsets = [question_form.option_formset for question_form in question_formset]

        questions = question_formset.save(commit=False)
        optionss = [option_formset.save(commit=False) for option_formset in option_formsets]

    # Assign indices and related instances to the new objects.

    for question_index, (question, options) in enumerate(zip(questions, optionss)):
        question.election = election
        question.index = question_index
        for option_index, option in enumerate(options):
            option.question = question
            option.index = option_index

    return questions, optionss
