from __future__ import absolute_import, division, print_function, unicode_literals

from django import forms
from django.db import transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, ungettext_lazy

from demos_voting.ballot_distributor.models import BallotArchive, Election, VoterList
from demos_voting.ballot_distributor.tasks import process_ballot_archive, process_voter_list
from demos_voting.base.fields import MultiEmailField


class CreateBallotArchiveForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.election = kwargs.pop('election')
        self.user = kwargs.pop('user')
        super(CreateBallotArchiveForm, self).__init__(*args, **kwargs)
        self.fields['ballot_count'].min_value = 1
        self.fields['ballot_count'].max_value = self.election.remaining_ballot_count
        self.fields['language'].initial = self.election.communication_language
        self.fields['language'].choices = self.fields['language'].choices[1:]

    def clean(self):
        cleaned_data = super(CreateBallotArchiveForm, self).clean()
        election = self.election
        # Check the election's visibility.
        if election.visibility == election.VISIBILITY_PRIVATE:
            raise forms.ValidationError(
                _("Ballot archives cannot be created because the election's visibility is private.")
            )
        # Check the election's state.
        if election.state != election.STATE_BALLOT_DISTRIBUTION:
            raise forms.ValidationError(
                _("New ballots cannot be generated because the election is not in the ballot distribution phase.")
            )
        elif timezone.now() >= election.voting_starts_at:
            raise forms.ValidationError(
                _("New ballots cannot be generated because the ballot distribution phase is about to end.")
            )
        # Check the number of remaining ballots.
        ballot_count = self.cleaned_data.get('ballot_count')
        if election.remaining_ballot_count == 0:
            self.add_error('ballot_count', forms.ValidationError(_("There are no ballots remaining.")))
        elif ballot_count > election.remaining_ballot_count:
            error = forms.ValidationError(
                ungettext_lazy(
                    "There is only one ballot remaining.",
                    "There are only %(ballot_count)d ballots remaining.", election.remaining_ballot_count
                ) % {'ballot_count': election.remaining_ballot_count},
            )
            self.add_error('ballot_count', error)
        return cleaned_data

    def save(self, commit=True):
        assert self.is_valid()
        ballot_archive = super(CreateBallotArchiveForm, self).save(commit=False)
        ballot_archive.election = self.election
        ballot_archive.administrator = self.election.administrators.get(user=self.user)
        if commit:
            ballot_archive.save()
            transaction.on_commit(lambda: process_ballot_archive.delay(ballot_archive.pk))
        return ballot_archive

    class Meta:
        model = BallotArchive
        fields = ['ballot_count', 'language']


class CreateVoterListForm(forms.ModelForm):
    emails = MultiEmailField(label=_("Voter email addresses"), required=False, case_insensitive=True, max_length=1000)

    def __init__(self, *args, **kwargs):
        self.election = kwargs.pop('election')
        self.user = kwargs.pop('user')
        super(CreateVoterListForm, self).__init__(*args, **kwargs)
        self.fields['file'].required = False
        self.fields['file'].label = _("Voter list file")
        self.fields['emails'].max_num = self.election.remaining_ballot_count

    def clean(self):
        cleaned_data = super(CreateVoterListForm, self).clean()
        election = self.election
        # Check the election's state.
        if election.state != election.STATE_BALLOT_DISTRIBUTION:
            raise forms.ValidationError(
                _("New voters cannot be registered because the election is not in the ballot distribution phase.")
            )
        elif timezone.now() >= election.voting_starts_at:
            raise forms.ValidationError(
                _("New voters cannot be registered because the ballot distribution phase is about to end.")
            )
        # Check the number of remaining ballots.
        if election.remaining_ballot_count == 0:
            self.add_error('emails', forms.ValidationError(_("There are no ballots remaining.")))
        # Either `file` or `emails` must be provided, not both.
        voter_list_file = self.cleaned_data.get('file')
        voter_emails = self.cleaned_data.get('emails')
        if 'file' not in self.errors and 'emails' not in self.errors:
            if bool(voter_list_file is not None) == bool(voter_emails):  # xnor
                raise forms.ValidationError(
                    _("Please submit either a voter list file or a list of email addresses.")
                )
        if voter_emails:
            # Filter out the voters that already exist (they should have
            # already received their ballots) and compare the number of the
            # remaining voters with the number of the remaining ballots.
            new_voter_count = 0
            for email in voter_emails:
                if not election.voters.filter(email__iexact=email).exists():
                    new_voter_count += 1
                    if new_voter_count > election.remaining_ballot_count:
                        error = forms.ValidationError(
                            ungettext_lazy(
                                "There is only one ballot remaining.",
                                "There are only %(ballot_count)d ballots remaining.", election.remaining_ballot_count
                            ) % {'ballot_count': election.remaining_ballot_count},
                        )
                        self.add_error('emails', error)
        return cleaned_data

    def save(self, commit=True):
        assert self.is_valid()
        election = self.election
        voter_list = super(CreateVoterListForm, self).save(commit=False)
        voter_list.election = election
        voter_list.administrator = election.administrators.get(user=self.user)
        if commit:
            voter_list.save()
            voter_emails = self.cleaned_data.get('emails')
            if voter_emails:
                # Save the new voters.
                assert self.cleaned_data.get('file') is None
                for email in voter_emails:
                    voter, created = election.voters.get_or_create(email__iexact=email, defaults={'email': email})
                    voter_list.voters.add(voter)
            # Start the task that will process the voter list.
            transaction.on_commit(lambda: process_voter_list.delay(voter_list.pk))
        return voter_list

    class Meta:
        model = VoterList
        fields = ['file']


class UpdateElectionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(UpdateElectionForm, self).__init__(*args, **kwargs)
        if 'cancel-election' in self.data:
            self.fields.clear()

    def clean(self):
        cleaned_data = super(UpdateElectionForm, self).clean()
        election = self.instance
        if election.state != election.STATE_BALLOT_DISTRIBUTION:
            raise forms.ValidationError(_("The election is not in the ballot distribution phase."))
        return cleaned_data

    def save(self, commit=True):
        election = self.instance
        if 'cancel-election' in self.data:
            election.state = election.STATE_CANCELLED
            election.ballot_distribution_ended_at = timezone.now()
        return super(UpdateElectionForm, self).save(commit=commit)

    class Meta:
        model = Election
        fields = []
