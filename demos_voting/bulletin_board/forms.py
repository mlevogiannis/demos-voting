from __future__ import absolute_import, division, print_function, unicode_literals

from django import forms
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from demos_voting.bulletin_board.models import Election


class UpdateElectionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(UpdateElectionForm, self).__init__(*args, **kwargs)
        if 'cancel-election' in self.data:
            self.fields.clear()

    def clean(self):
        cleaned_data = super(UpdateElectionForm, self).clean()
        election = self.instance
        if election.state != election.STATE_TALLY:
            raise forms.ValidationError(_("The election is not in the tally phase."))
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


class TallyForm(forms.ModelForm):
    class Meta:
        model = Election
        fields = []
