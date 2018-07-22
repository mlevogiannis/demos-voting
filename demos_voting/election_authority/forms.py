from __future__ import absolute_import, division, print_function, unicode_literals

from django import forms
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, MaxLengthValidator
from django.db import transaction
from django.utils import timezone, translation
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from six.moves import range

from demos_voting.base.fields import MultiEmailField
from demos_voting.election_authority.models import Administrator, Election, ElectionOption, ElectionQuestion, Trustee
from demos_voting.election_authority.tasks import prepare_setup_phase

NAME_MAX_LENGTH = 1000


class CreateElectionForm(forms.ModelForm):
    prefix = 'election'

    trustee_emails = MultiEmailField(
        label=_("Trustee email addresses"),
        min_num=1,
        max_num=settings.DEMOS_VOTING_MAX_TRUSTEES,
        case_insensitive=True,
    )
    enable_security_code = forms.BooleanField(
        label=_("Enable security code"),
        initial=True,
        required=False,
    )

    # Party-candidate specific fields.
    max_candidate_selection_count = forms.IntegerField(
        label=_("Maximum number of candidate selections"),
        required=False,
        min_value=1,
    )
    candidate_option_table_layout = forms.ChoiceField(
        label=_("Candidate table layout"),
        required=False,
        choices=ElectionQuestion.OPTION_TABLE_LAYOUT_CHOICES,
        initial=ElectionQuestion.OPTION_TABLE_LAYOUT_1_COLUMN,
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(CreateElectionForm, self).__init__(*args, **kwargs)
        # Editing existing elections is not supported.
        assert self.instance.pk is None
        # Initialize question-option formset.
        self.question_formset_kwargs = {
            'instance': self.instance,
            'prefix': CreateQuestionForm.prefix,
            'election_form': self,
        }
        self.question_formset = CreateQuestionFormSet(data=self.data or None, **self.question_formset_kwargs)
        # Initialize party-candidate formset.
        self.party_question = ElectionQuestion(election=self.instance, index=0, name=None)
        self.candidate_question = ElectionQuestion(election=self.instance, index=1, name=None)
        self.party_formset_kwargs = {
            'instance': self.party_question,
            'prefix': CreatePartyForm.prefix,
            'election_form': self,
        }
        self.party_formset = CreatePartyFormSet(data=self.data or None, **self.party_formset_kwargs)
        # Set extra field arguments.
        name_field = self.fields['name']
        name_field.max_length = NAME_MAX_LENGTH
        name_field.validators.append(MaxLengthValidator(name_field.max_length))
        ballot_count_field = self.fields['ballot_count']
        ballot_count_field.min_value = 1
        ballot_count_field.validators.append(MinValueValidator(ballot_count_field.min_value))
        ballot_count_field.max_value = settings.DEMOS_VOTING_MAX_BALLOTS
        ballot_count_field.validators.append(MaxValueValidator(ballot_count_field.max_value))
        communication_language_field = self.fields['communication_language']
        communication_language_field.initial = translation.get_language()
        communication_language_field.choices = communication_language_field.choices[1:]
        try:
            max_candidate_count = max(f.candidate_formset.total_form_count() for f in self.party_formset)
        except (ValueError, forms.ValidationError):
            max_candidate_count = 0
        max_candidate_selection_count_field = self.fields['max_candidate_selection_count']
        max_candidate_selection_count_field.max_value = max(1, max_candidate_count)
        max_candidate_selection_count_field.validators.append(
            MaxValueValidator(max_candidate_selection_count_field.max_value)
        )

    def clean_voting_starts_at(self):
        voting_starts_at = self.cleaned_data['voting_starts_at']
        if voting_starts_at <= timezone.now():
            raise forms.ValidationError(_("The voting start time cannot be in the past."), code='invalid')
        return voting_starts_at

    def clean_voting_ends_at(self):
        voting_ends_at = self.cleaned_data['voting_ends_at']
        if voting_ends_at <= timezone.now():
            raise forms.ValidationError(_("The voting end time cannot be in the past."), code='invalid')
        return voting_ends_at

    def clean(self):
        cleaned_data = super(CreateElectionForm, self).clean()
        election_type = cleaned_data.get('type')
        # Unbind the unused formset to prevent false errors.
        if election_type != Election.TYPE_QUESTION_OPTION:
            self.question_formset = CreateQuestionFormSet(**self.question_formset_kwargs)
        if election_type != Election.TYPE_PARTY_CANDIDATE:
            self.party_formset = CreatePartyFormSet(**self.party_formset_kwargs)
        # The start time must be before the end time.
        voting_starts_at = cleaned_data.get('voting_starts_at')
        voting_ends_at = cleaned_data.get('voting_ends_at')
        if voting_starts_at is not None and voting_ends_at is not None and voting_starts_at >= voting_ends_at:
            error = _("The start time must be before the end time.")
            self.add_error(None, forms.ValidationError(error, code='invalid'))
        # Party-candidate specific validation.
        if election_type == Election.TYPE_PARTY_CANDIDATE:
            max_candidate_selection_count = cleaned_data.get('max_candidate_selection_count')
            if max_candidate_selection_count is None:
                error = forms.ValidationError(forms.Field.default_error_messages['required'], code='required')
                self.add_error('max_candidate_selection_count', error)
            candidate_option_table_layout = cleaned_data.get('candidate_option_table_layout')
            if not candidate_option_table_layout:
                error = forms.ValidationError(forms.Field.default_error_messages['required'], code='required')
                self.add_error('candidate_option_table_layout', error)
        return cleaned_data

    def is_valid(self):
        election_form_is_valid = super(CreateElectionForm, self).is_valid()
        election_type = self.cleaned_data.get('type')
        try:
            if election_type == Election.TYPE_QUESTION_OPTION:
                question_or_party_formset_is_valid = self.question_formset.is_valid()
            elif election_type == Election.TYPE_PARTY_CANDIDATE:
                question_or_party_formset_is_valid = self.party_formset.is_valid()
        except forms.ValidationError:
            question_or_party_formset_is_valid = False
        return election_form_is_valid and question_or_party_formset_is_valid

    def save(self, commit=True):
        assert self.is_valid()
        election = super(CreateElectionForm, self).save(commit=False)
        if election.type == election.TYPE_QUESTION_OPTION:
            election._questions = self.question_formset.save(commit=False)
        elif election.type == election.TYPE_PARTY_CANDIDATE:
            election._questions = [self.party_question, self.candidate_question]
            # Set the party question's attributes.
            self.party_question.min_selection_count = 1
            self.party_question.max_selection_count = 1
            # Set the candidate question's attributes.
            max_candidate_selection_count = self.cleaned_data['max_candidate_selection_count']
            self.candidate_question.min_selection_count = max_candidate_selection_count
            self.candidate_question.max_selection_count = max_candidate_selection_count
            self.candidate_question.option_table_layout = self.cleaned_data['candidate_option_table_layout']
        # Save the objects.
        if commit:
            election.save()
        self._save_administrators(commit=commit)
        self._save_trustees(commit=commit)
        if election.type == election.TYPE_QUESTION_OPTION:
            election._questions = self.question_formset.save(commit=commit)
        elif election.type == election.TYPE_PARTY_CANDIDATE:
            election._questions = self._save_parties_and_candidates(commit=commit)
        # Generate the remaining election attributes.
        update_fields = []
        if election.vote_code_type == election.VOTE_CODE_TYPE_SHORT:
            if self.cleaned_data.get('enable_security_code'):
                election.generate_security_code_length()
                if commit:
                    update_fields.append('security_code_length')
        elif election.vote_code_type == election.VOTE_CODE_TYPE_LONG:
            election.generate_vote_code_length()
            if commit:
                update_fields.append('vote_code_length')
        if update_fields:
            election.save(update_fields=update_fields)
        # Start the setup task.
        if commit:
            transaction.on_commit(lambda: prepare_setup_phase.delay(election.pk))
        return election

    @property
    def _candidate_count_per_party(self):
        if not self.is_valid():
            raise AttributeError
        party_count = self.party_formset.total_form_count() + 1
        max_candidate_count = max(f.candidate_formset.total_form_count() for f in self.party_formset)
        max_candidate_selection_count = self.cleaned_data['max_candidate_selection_count']
        candidate_count = party_count * (max_candidate_count + max_candidate_selection_count)
        return candidate_count // party_count

    def _save_administrators(self, commit=True):
        administrator = Administrator(election=self.instance, user=self.user)
        if commit:
            administrator.save()
        return [administrator]

    def _save_trustees(self, commit=True):
        trustees = [Trustee(election=self.instance, email=email) for email in self.cleaned_data['trustee_emails']]
        if commit:
            Trustee.objects.bulk_create(trustees)
        return trustees

    def _save_parties_and_candidates(self, commit=True):
        assert self.is_valid() and self.instance.type == self.instance.TYPE_PARTY_CANDIDATE
        if commit:
            self.party_question.election = self.instance
            self.party_question.save()
            self.candidate_question.election = self.instance
            self.candidate_question.save()
        party_election_options = self.party_formset.save(commit=commit)
        candidate_election_options = []
        for party_form in self.party_formset:
            candidate_election_options.extend(party_form.candidate_formset.save(commit=commit))
        blank_party_election_option = self._save_blank_party(commit=commit)
        party_election_options.append(blank_party_election_option)
        party_election_options.sort(key=lambda o: o.index)
        blank_candidate_election_options = self._save_blank_candidates(commit=commit)
        candidate_election_options.extend(blank_candidate_election_options)
        candidate_election_options.sort(key=lambda o: o.index)
        self.party_question._options = party_election_options
        self.candidate_question._options = candidate_election_options
        return [self.party_question, self.candidate_question]

    def _save_blank_party(self, commit=False):
        blank_party_option = ElectionOption(
            question=self.party_question,
            index=self.party_formset.total_form_count(),
            name=None,
        )
        if commit:
            blank_party_option.save()
        return blank_party_option

    def _save_blank_candidates(self, commit=False):
        parties = [
            (index, form.candidate_formset.total_form_count())
            for index, form in enumerate(self.party_formset.ordered_forms)
        ]
        parties.append((self.party_formset.total_form_count(), 0))  # blank party
        blank_candidate_options = []
        for party_index, non_blank_candidate_count in parties:
            blank_candidate_options.extend([
                ElectionOption(
                    question=self.candidate_question,
                    index=party_index * self._candidate_count_per_party + non_blank_candidate_count + i,
                    name=None,
                )
                for i in range(self._candidate_count_per_party - non_blank_candidate_count)
            ])
        if commit:
            ElectionOption.objects.bulk_create(blank_candidate_options)
        return blank_candidate_options

    class Meta:
        model = Election
        fields = [
            'slug', 'name', 'voting_starts_at', 'voting_ends_at', 'type', 'vote_code_type', 'visibility',
            'communication_language', 'ballot_count', 'trustee_emails', 'enable_security_code',
            'max_candidate_selection_count', 'candidate_option_table_layout',
        ]
        widgets = {
            'name': forms.TextInput,
            'type': forms.RadioSelect,
            'vote_code_type': forms.RadioSelect,
            'visibility': forms.RadioSelect,
        }


class CreateQuestionForm(forms.ModelForm):
    prefix = 'question'

    def __init__(self, *args, **kwargs):
        self.index = kwargs.pop('index', None)
        super(CreateQuestionForm, self).__init__(*args, **kwargs)
        self.option_formset = CreateOptionFormSet(
            data=self.data or None,
            instance=self.instance,
            prefix='%s-%s' % (self.prefix, CreateOptionForm.prefix),
        )
        # Set extra field arguments.
        name_field = self.fields['name']
        name_field.required = True
        name_field.max_length = NAME_MAX_LENGTH
        name_field.validators.append(MaxLengthValidator(name_field.max_length))
        min_selection_count_field = self.fields['min_selection_count']
        min_selection_count_field.min_value = 0
        min_selection_count_field.validators.append(MinValueValidator(min_selection_count_field.min_value))
        max_selection_count_field = self.fields['max_selection_count']
        max_selection_count_field.min_value = 1
        max_selection_count_field.validators.append(MinValueValidator(max_selection_count_field.min_value))
        try:
            option_count = self.option_formset.total_form_count()
        except forms.ValidationError:
            option_count = 0
        min_selection_count_field.max_value = max(0, option_count - 1)
        min_selection_count_field.validators.append(MaxValueValidator(min_selection_count_field.max_value))
        max_selection_count_field.max_value = max(1, option_count)
        max_selection_count_field.validators.append(MaxValueValidator(max_selection_count_field.max_value))

    def clean(self):
        cleaned_data = super(CreateQuestionForm, self).clean()
        # The minimum number of selections cannot be greater than the maximum
        # number of selections.
        min_selection_count = cleaned_data.get('min_selection_count')
        max_selection_count = cleaned_data.get('max_selection_count')
        if min_selection_count is not None and max_selection_count is not None:
            if min_selection_count > max_selection_count:
                error = _("The minimum number of selections cannot be greater than the maximum number of selections.")
                self.add_error(None, forms.ValidationError(error, code='invalid'))
        return cleaned_data

    def is_valid(self):
        try:
            option_formset_is_valid = self.option_formset.is_valid()
        except forms.ValidationError:
            option_formset_is_valid = False
        return super(CreateQuestionForm, self).is_valid() and option_formset_is_valid

    def save(self, commit=True):
        assert self.is_valid()
        self.instance.index = self.index
        return super(CreateQuestionForm, self).save(commit=commit)

    class Meta:
        model = ElectionQuestion
        fields = ['name', 'min_selection_count', 'max_selection_count', 'option_table_layout']
        widgets = {
            'name': forms.TextInput,
            'option_table_layout': forms.RadioSelect,
        }


class BaseCreateQuestionFormSet(forms.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.election_form = kwargs.pop('election_form')
        super(BaseCreateQuestionFormSet, self).__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super(BaseCreateQuestionFormSet, self).get_form_kwargs(index)
        kwargs['index'] = index
        return kwargs

    def clean(self):
        super(BaseCreateQuestionFormSet, self).clean()
        if any(self.errors):
            return
        # Validate that each question has a unique name.
        names = set()
        for form in self.forms:
            name = form.cleaned_data['name']
            if name in names:
                raise forms.ValidationError(_("Each question must have a unique name."))
            names.add(name)
        # Ensure that not all questions have a minimum number of selections
        # equal to zero when using long vote-codes.
        election_type = self.election_form.cleaned_data['type']
        if election_type == Election.TYPE_QUESTION_OPTION:
            vote_code_type = self.election_form.cleaned_data['vote_code_type']
            if vote_code_type == Election.VOTE_CODE_TYPE_LONG:
                if all(form.cleaned_data['min_selection_count'] == 0 for form in self.forms):
                    raise forms.ValidationError(
                        _("At least one question must have a minimum number of selections greater or equal to 1 when "
                          "the vote-code type is long.")
                    )

    def save(self, commit=True):
        questions = super(BaseCreateQuestionFormSet, self).save(commit=commit)
        for question_form in self.forms:
            question_form.instance._options = question_form.option_formset.save(commit=commit)
        return questions


CreateQuestionFormSet = forms.inlineformset_factory(
    parent_model=Election,
    model=ElectionQuestion,
    form=CreateQuestionForm,
    formset=BaseCreateQuestionFormSet,
    extra=-1,
    can_delete=True,
    can_order=True,
    validate_min=True,
    validate_max=True,
    min_num=1,
    max_num=settings.DEMOS_VOTING_MAX_QUESTIONS,
)


class CreateOptionForm(forms.ModelForm):
    prefix = 'option'

    def __init__(self, *args, **kwargs):
        self.index = kwargs.pop('index', None)
        super(CreateOptionForm, self).__init__(*args, **kwargs)
        # Set extra field arguments.
        name_field = self.fields['name']
        name_field.required = True
        name_field.max_length = NAME_MAX_LENGTH
        name_field.validators.append(MaxLengthValidator(name_field.max_length))

    def save(self, commit=True):
        assert self.is_valid()
        self.instance.index = self.index
        return super(CreateOptionForm, self).save(commit=commit)

    class Meta:
        model = ElectionOption
        fields = ['name']
        widgets = {
            'name': forms.TextInput,
        }


class BaseCreateOptionFormSet(forms.BaseInlineFormSet):
    def get_form_kwargs(self, index):
        kwargs = super(BaseCreateOptionFormSet, self).get_form_kwargs(index)
        kwargs['index'] = index
        return kwargs

    def clean(self):
        super(BaseCreateOptionFormSet, self).clean()
        if any(self.errors):
            return
        # Validate that each option has a unique name.
        names = set()
        for form in self.forms:
            name = form.cleaned_data['name']
            if name in names:
                raise forms.ValidationError(_("Each option must have a unique name."))
            names.add(name)


CreateOptionFormSet = forms.inlineformset_factory(
    parent_model=ElectionQuestion,
    model=ElectionOption,
    form=CreateOptionForm,
    formset=BaseCreateOptionFormSet,
    extra=-2,
    can_delete=True,
    can_order=True,
    validate_min=True,
    validate_max=True,
    min_num=2,
    max_num=settings.DEMOS_VOTING_MAX_OPTIONS,
)


class CreatePartyForm(forms.ModelForm):
    prefix = 'party'

    def __init__(self, *args, **kwargs):
        self.party_formset = kwargs.pop('party_formset')
        super(CreatePartyForm, self).__init__(*args, **kwargs)
        self.candidate_formset = CreateCandidateFormSet(
            data=self.data or None,
            instance=self.party_formset.election_form.candidate_question,
            prefix='%s-%s' % (self.prefix, CreateCandidateForm.prefix),
            party_form=self,
        )
        # Set extra field arguments.
        name_field = self.fields['name']
        name_field.required = True
        name_field.max_length = NAME_MAX_LENGTH
        name_field.validators.append(MaxLengthValidator(name_field.max_length))

    def is_valid(self):
        try:
            candidate_formset_is_valid = self.candidate_formset.is_valid()
        except forms.ValidationError:
            candidate_formset_is_valid = False
        return super(CreatePartyForm, self).is_valid() and candidate_formset_is_valid

    def save(self, commit=True):
        assert self.is_valid()
        self.instance.index = self.party_formset.ordered_forms.index(self)
        return super(CreatePartyForm, self).save(commit=commit)

    class Meta:
        model = ElectionOption
        fields = ['name']
        widgets = {
            'name': forms.TextInput,
        }


class BaseCreatePartyFormSet(forms.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.election_form = kwargs.pop('election_form')
        super(BaseCreatePartyFormSet, self).__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super(BaseCreatePartyFormSet, self).get_form_kwargs(index)
        kwargs['party_formset'] = self
        return kwargs

    @cached_property
    def ordered_forms(self):
        assert self.is_valid()
        return sorted(self.forms, key=lambda form: form.instance.name)

    def clean(self):
        super(BaseCreatePartyFormSet, self).clean()
        if any(self.errors):
            return
        # Validate that each party has a unique name.
        names = set()
        for form in self.forms:
            name = form.cleaned_data['name']
            if name in names:
                raise forms.ValidationError(_("Each party must have a unique name."))
            names.add(name)

    def save(self, commit=True):
        parties = super(BaseCreatePartyFormSet, self).save(commit=commit)
        if commit:
            for party_form in self.forms:
                party_form.candidate_formset.save(commit=True)
        return parties


CreatePartyFormSet = forms.inlineformset_factory(
    parent_model=ElectionQuestion,
    model=ElectionOption,
    form=CreatePartyForm,
    formset=BaseCreatePartyFormSet,
    extra=-1,
    can_delete=True,
    can_order=False,
    validate_min=True,
    validate_max=True,
    min_num=1,
    max_num=settings.DEMOS_VOTING_MAX_PARTIES,
)


class CreateCandidateForm(forms.ModelForm):
    prefix = 'candidate'

    def __init__(self, *args, **kwargs):
        self.candidate_formset = kwargs.pop('candidate_formset')
        super(CreateCandidateForm, self).__init__(*args, **kwargs)
        # Set extra field arguments.
        name_field = self.fields['name']
        name_field.required = True
        name_field.max_length = NAME_MAX_LENGTH
        name_field.validators.append(MaxLengthValidator(name_field.max_length))

    def save(self, commit=True):
        assert self.is_valid()
        election_form = self.candidate_formset.party_form.party_formset.election_form
        candidate_count_per_party = election_form._candidate_count_per_party
        party_index = self.candidate_formset.party_form.instance.index
        candidate_index = self.candidate_formset.ordered_forms.index(self)
        self.instance.index = party_index * candidate_count_per_party + candidate_index
        return super(CreateCandidateForm, self).save(commit=commit)

    class Meta:
        model = ElectionOption
        fields = ['name']
        widgets = {
            'name': forms.TextInput,
        }


class BaseCreateCandidateFormSet(forms.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.party_form = kwargs.pop('party_form')
        super(BaseCreateCandidateFormSet, self).__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super(BaseCreateCandidateFormSet, self).get_form_kwargs(index)
        kwargs['candidate_formset'] = self
        return kwargs

    @cached_property
    def ordered_forms(self):
        assert self.is_valid()
        return sorted(self.forms, key=lambda form: form.instance.name)

    def clean(self):
        super(BaseCreateCandidateFormSet, self).clean()
        if any(self.errors):
            return
        # Validate that each candidate has a unique name.
        names = set()
        for form in self.forms:
            name = form.cleaned_data['name']
            if name in names:
                raise forms.ValidationError(_("Each candidate must have a unique name."))
            names.add(name)


CreateCandidateFormSet = forms.inlineformset_factory(
    parent_model=ElectionQuestion,
    model=ElectionOption,
    form=CreateCandidateForm,
    formset=BaseCreateCandidateFormSet,
    extra=-1,
    can_delete=True,
    can_order=False,
    validate_min=True,
    validate_max=True,
    min_num=1,
    max_num=settings.DEMOS_VOTING_MAX_CANDIDATES,
)


class UpdateElectionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(UpdateElectionForm, self).__init__(*args, **kwargs)
        if 'cancel-election' in self.data:
            self.fields.clear()

    def clean(self):
        cleaned_data = super(UpdateElectionForm, self).clean()
        election = self.instance
        if election.state != election.STATE_SETUP:
            raise forms.ValidationError(_("The election is not in the setup phase."))
        return cleaned_data

    def save(self, commit=True):
        election = self.instance
        if 'cancel-election' in self.data:
            election.state = election.STATE_CANCELLED
            election.setup_ended_at = timezone.now()
        return super(UpdateElectionForm, self).save(commit=commit)

    class Meta:
        model = Election
        fields = []
