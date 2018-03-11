from __future__ import absolute_import, division, print_function, unicode_literals

from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from demos_voting.base.models import (
    BaseAdministrator, BaseBallot, BaseBallotOption, BaseBallotPart, BaseBallotQuestion, BaseElection,
    BaseElectionOption, BaseElectionQuestion,
)


class Election(BaseElection):
    STATE_CHOICES = (
        (BaseElection.STATE_SETUP, _("Setup")),
        (BaseElection.STATE_BALLOT_DISTRIBUTION, _("Ballot distribution")),
        (BaseElection.STATE_VOTING, _("Voting")),
        (BaseElection.STATE_COMPLETED, _("Completed")),
        (BaseElection.STATE_FAILED, _("Failed")),
        (BaseElection.STATE_CANCELLED, _("Cancelled")),
    )

    state = models.CharField(_("state"), max_length=32, choices=STATE_CHOICES, default=BaseElection.STATE_SETUP)
    voting_started_at = models.DateTimeField(_("voting started at"), null=True, blank=True)
    voting_ended_at = models.DateTimeField(_("voting ended at"), null=True, blank=True)

    def get_absolute_url(self):
        return reverse('vote-collector:election-detail', args=[self.slug])


class ElectionQuestion(BaseElectionQuestion):
    pass


class ElectionOption(BaseElectionOption):
    pass


class Ballot(BaseBallot):
    pass


class BallotPart(BaseBallotPart):
    credential = models.TextField(_("credential"), null=True, blank=True, default=None)
    credential_hash = models.TextField(_("credential hash"))
    is_cast = models.BooleanField(_("is cast"), default=False)


class BallotQuestion(BaseBallotQuestion):
    pass


class BallotOption(BaseBallotOption):
    vote_code = models.TextField(_("vote-code"), null=True, blank=True, default=None)
    vote_code_hash = models.TextField(_("vote-code hash"), null=True, blank=True, default=None)
    is_voted = models.BooleanField(_("is voted"), default=False)


class Administrator(BaseAdministrator):
    pass
