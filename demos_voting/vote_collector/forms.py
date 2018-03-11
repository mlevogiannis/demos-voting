from __future__ import absolute_import, division, print_function, unicode_literals

from django import forms
from django.db import transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from six.moves import zip

from demos_voting.base.utils import base32, hasher
from demos_voting.vote_collector.models import BallotPart, Election
from demos_voting.vote_collector.tasks import extend_voting_period


class VotingBoothBallotPartForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.credential = kwargs.pop('credential', None)
        super(VotingBoothBallotPartForm, self).__init__(*args, **kwargs)
        ballot_part = self.instance
        if ballot_part.pk:
            self.election = ballot_part.election
            self.option_formsets = []
            for election_question, ballot_question in zip(self.election.questions.all(), ballot_part.questions.all()):
                option_formset_class = forms.formset_factory(
                    form=VotingBoothBallotOptionForm,
                    formset=BaseVotingBoothBallotOptionFormSet,
                    extra=election_question.max_selection_count - election_question.min_selection_count,
                    validate_min=True,
                    validate_max=True,
                    min_num=election_question.min_selection_count,
                    max_num=election_question.max_selection_count,
                )
                option_formset = option_formset_class(
                    data=self.data or None,
                    prefix='question-%d-option' % election_question.index,
                    election_question=election_question,
                    ballot_question=ballot_question,
                )
                self.option_formsets.append(option_formset)

    def clean(self):
        timezone_now = timezone.now()
        cleaned_data = super(VotingBoothBallotPartForm, self).clean()
        # Validate the vote-codes. Since the exact errors are not returned to
        # the user (for privacy reasons), validation can stop at the first
        # invalid vote-code.
        if not all(option_formset.is_valid() for option_formset in self.option_formsets):
            raise forms.ValidationError(_("One or more of the submitted vote-codes are not valid."))
        # Validate that the selected candidate options correspond to the
        # selected party option.
        if self.election.type == self.election.TYPE_PARTY_CANDIDATE:
            party_formset, candidate_formset = self.option_formsets
            party_ballot_option = party_formset.ballot_options[0]
            candidate_ballot_options = candidate_formset.ballot_options
            party_count = party_formset.election_question.option_count
            candidate_count = candidate_formset.election_question.option_count
            candidate_count_per_party = candidate_count // party_count
            min_index = party_ballot_option.index * candidate_count_per_party
            max_index = (party_ballot_option.index + 1) * candidate_count_per_party - 1
            for candidate_ballot_option in candidate_ballot_options:
                if candidate_ballot_option.index < min_index or candidate_ballot_option.index > max_index:
                    raise forms.ValidationError(
                        _("One or more candidate vote-codes do not correspond to the party vote-code.")
                    )
        return cleaned_data

    def save(self, commit=True):
        assert self.is_valid()
        update_fields = []
        ballot_part = self.instance
        ballot_part.is_cast = True
        update_fields.append('is_cast')
        if self.election.vote_code_type == self.election.VOTE_CODE_TYPE_SHORT:
            ballot_part.credential = self.credential
            update_fields.append('credential')
        if commit:
            ballot_part.save(update_fields=update_fields)
            for option_formset in self.option_formsets:
                ballot_question = option_formset.ballot_question
                if self.election.vote_code_type == self.election.VOTE_CODE_TYPE_SHORT:
                    # Mark the options as voted.
                    option_formset.ballot_options.update(is_voted=True)
                elif self.election.vote_code_type == self.election.VOTE_CODE_TYPE_LONG:
                    # Restore the options' vote-codes and mark them as voted.
                    for ballot_option in option_formset.ballot_options.iterator():
                        ballot_option.is_voted = True
                        ballot_option.vote_code = option_formset.hash_to_vote_code[ballot_option.vote_code_hash]
                        ballot_option.save(update_fields=['is_voted', 'vote_code'])
        return ballot_part

    class Meta:
        model = BallotPart
        fields = []


class BaseVotingBoothBallotOptionFormSet(forms.BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.election_question = kwargs.pop('election_question')
        self.election = self.election_question.election
        self.ballot_question = kwargs.pop('ballot_question')
        self.ballot_options = None
        self.hash_to_vote_code = None
        super(BaseVotingBoothBallotOptionFormSet, self).__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super(BaseVotingBoothBallotOptionFormSet, self).get_form_kwargs(index)
        kwargs['election_question'] = self.election_question
        return kwargs

    def clean(self):
        super(BaseVotingBoothBallotOptionFormSet, self).clean()
        if any(self.errors):
            return
        # Check for duplicate vote-codes.
        vote_codes = set()
        for form in self.forms:
            vote_code = form.cleaned_data.get('vote_code')
            if vote_code is not None:
                if vote_code in vote_codes:
                    raise forms.ValidationError("Duplicate vote-code.")
                vote_codes.add(vote_code)
        # Get the options that correspond to the submitted vote-codes.
        if self.election.vote_code_type == self.election.VOTE_CODE_TYPE_SHORT:
            # Get the ballot options by their vote-codes.
            self.ballot_options = self.ballot_question.options.filter(vote_code__in=vote_codes)
        elif self.election.vote_code_type == self.election.VOTE_CODE_TYPE_LONG:
            # The vote-code hashes of a ballot question share the same hash
            # salt and number of iterations. Fetch a random hash to get those
            # parameters.
            hash_summary = hasher.summary(self.ballot_question.options.values_list('vote_code_hash', flat=True)[0])
            salt = hash_summary['salt']
            iterations = hash_summary['iterations']
            # Get the ballot options by their vote-code hashes.
            self.hash_to_vote_code = {
                hasher.encode(vote_code, salt, iterations): vote_code
                for vote_code in vote_codes
            }
            self.ballot_options = self.ballot_question.options.filter(vote_code_hash__in=self.hash_to_vote_code.keys())
            # Check for invalid vote-codes.
            if self.ballot_options.count() != len(vote_codes):
                raise forms.ValidationError("One or more invalid vote-codes.")


class VotingBoothBallotOptionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        election_question = kwargs.pop('election_question')
        self.election = election_question.election
        super(VotingBoothBallotOptionForm, self).__init__(*args, **kwargs)
        if self.election.vote_code_type == self.election.VOTE_CODE_TYPE_SHORT:
            self.fields['vote_code'] = forms.IntegerField(
                min_value=1,
                max_value=election_question.option_count,
                error_messages={'invalid': "Invalid vote-code."},
            )
        elif self.election.vote_code_type == self.election.VOTE_CODE_TYPE_LONG:
            self.fields['vote_code'] = forms.CharField(
                min_length=self.election.vote_code_length,
                max_length=2 * self.election.vote_code_length - 1,
                error_messages={'invalid': "Invalid vote-code."},
            )

    def clean_vote_code(self):
        vote_code = self.cleaned_data['vote_code']
        if self.election.vote_code_type == self.election.VOTE_CODE_TYPE_LONG:
            try:
                vote_code = base32.normalize(vote_code)  # raises ValueError
                if len(vote_code) != self.election.vote_code_length:
                    raise ValueError
            except ValueError:
                raise forms.ValidationError(self.fields['vote_code'].error_messages['invalid'], code='invalid')
        return vote_code


class UpdateElectionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(UpdateElectionForm, self).__init__(*args, **kwargs)
        if 'cancel-election' in self.data:
            self.fields.clear()
        else:
            self.fields['voting_ends_at'].required = False

    def clean(self):
        cleaned_data = super(UpdateElectionForm, self).clean()
        election = self.instance
        if election.state != election.STATE_VOTING:
            raise forms.ValidationError(_("The election is not in the voting phase."))
        voting_ends_at = self.cleaned_data.get('voting_ends_at')
        if voting_ends_at is not None and voting_ends_at <= election.voting_ends_at:
            e = _("The new voting end time must be after the old voting end time.")
            self.add_error('voting_ends_at', forms.ValidationError(e, code='invalid'))
        return cleaned_data

    def save(self, commit=True):
        election = self.instance
        if 'cancel-election' in self.data:
            election.state = election.STATE_CANCELLED
            election.voting_ended_at = timezone.now()
        else:
            if commit and 'voting_ends_at' in self.cleaned_data:
                transaction.on_commit(lambda: extend_voting_period.delay(election.pk))
        return super(UpdateElectionForm, self).save(commit=commit)

    class Meta:
        model = Election
        fields = ['voting_ends_at']
