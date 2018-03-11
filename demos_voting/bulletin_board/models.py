from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import hashlib

from django.conf import settings
from django.db import models
from django.db.models import Exists, OuterRef, Q
from django.urls import reverse
from django.utils.encoding import force_bytes, force_text
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from six.moves.urllib.parse import urljoin

from demos_voting.base.fields import JSONField
from demos_voting.base.models import (
    BaseAdministrator, BaseBallot, BaseBallotOption, BaseBallotPart, BaseBallotQuestion, BaseElection,
    BaseElectionOption, BaseElectionQuestion, BaseTrustee, BaseVoter,
)
from demos_voting.bulletin_board.managers import BallotOptionManager, BallotQuestionManager
from demos_voting.bulletin_board.utils import crypto


class Election(BaseElection):
    STATE_CHOICES = (
        (BaseElection.STATE_SETUP, _("Setup")),
        (BaseElection.STATE_BALLOT_DISTRIBUTION, _("Ballot distribution")),
        (BaseElection.STATE_VOTING, _("Voting")),
        (BaseElection.STATE_TALLY, _("Tally")),
        (BaseElection.STATE_COMPLETED, _("Completed")),
        (BaseElection.STATE_FAILED, _("Failed")),
        (BaseElection.STATE_CANCELLED, _("Cancelled")),
    )

    coins = models.TextField(_("coins"), null=True, blank=True, default=None)
    state = models.CharField(_("state"), max_length=32, choices=STATE_CHOICES, default=BaseElection.STATE_SETUP)
    tally_started_at = models.DateTimeField(_("tally started at"), null=True, blank=True)
    tally_ended_at = models.DateTimeField(_("tally ended at"), null=True, blank=True)

    def get_absolute_url(self):
        return reverse('bulletin-board:election-detail', args=[self.slug])

    def generate_coins(self):
        """
        Generate the voters' coins.
        """
        # If a ballot's part A is cast then the ballot's coin is 0, if part B
        # is cast then the coin is 1. All unused ballots' coins are 0. The
        # coins are ordered by their ballots' serial numbers.
        cast_part_b_qs = BallotPart.objects.filter(ballot=OuterRef('pk'), tag=BallotPart.TAG_B, is_cast=True)
        coins = self.ballots.annotate(coin=Exists(cast_part_b_qs)).values_list('coin', flat=True)
        # Sha256-hash and base64-encode the result.
        h = hashlib.sha256()
        for coin in coins.iterator():
            h.update(force_bytes(int(coin)))
        self.coins = force_text(base64.b64encode(h.digest()))


class ElectionQuestion(BaseElectionQuestion):
    tally_commitment = JSONField(_("tally commitment"), null=True, blank=True, default=None)
    tally_decommitment = JSONField(_("tally decommitment"), null=True, blank=True, default=None)

    def generate_tally_commitment(self):
        ballot_options = BallotOption.objects.filter(question__in=self.ballot_questions.all(), is_voted=True)
        tally_commitments = ballot_options.values_list('commitment', flat=True)
        self.tally_commitment = crypto.add_com(tally_commitments.iterator())

    def generate_tally_decommitment(self):
        partial_tally_decommitments = self.partial_tally_decommitments.values_list('value', flat=True)
        self.tally_decommitment = crypto.add_decom(partial_tally_decommitments.iterator())

    @cached_property
    def total_vote_count(self):
        return self.options.aggregate(models.Sum('vote_count'))['vote_count__sum']

    @cached_property
    def _tally_plaintexts(self):
        return crypto.extract(self.election.commitment_key, self.tally_commitment, self.tally_decommitment,
                              self.election.ballot_count)


class ElectionOption(BaseElectionOption):
    vote_count = models.PositiveIntegerField(_("number of votes"), null=True, blank=True, default=None)

    def generate_vote_count(self):
        if self.is_blank:
            self.vote_count = None
        else:
            tally_plaintexts = self.question._tally_plaintexts
            if len(tally_plaintexts) > 0:
                non_blank_index = 0
                for option in self.question.options.all():
                    if self == option:
                        break
                    if not option.is_blank:
                        non_blank_index += 1
                self.vote_count = tally_plaintexts[non_blank_index]
            else:
                self.vote_count = 0  # no votes were submitted

    @cached_property
    def vote_percent(self):
        if self.vote_count is None:
            return None
        elif self.question.total_vote_count == 0:
            return 0.0
        else:
            return self.vote_count / self.question.total_vote_count


class Ballot(BaseBallot):
    pass


class BallotPart(BaseBallotPart):
    credential = models.TextField(_("credential"), null=True, blank=True, default=None)
    credential_hash = models.TextField(_("credential hash"))
    is_cast = models.BooleanField(_("is cast"), default=False)


class BallotQuestion(BaseBallotQuestion):
    zk1 = JSONField(_("zero-knowledge proof ZK1"))
    zk2 = JSONField(_("zero-knowledge proof ZK2"), null=True, blank=True, default=None)

    objects = BallotQuestionManager()

    def generate_zk2(self):
        if self.part.is_cast:
            pass  # FIXME
        else:
            self.zk2 = None


class BallotOption(BaseBallotOption):
    election_option = models.ForeignKey(
        'ElectionOption',
        on_delete=models.CASCADE,
        related_name='ballot_options',
        null=True,
        blank=True,
        default=None,
    )
    vote_code = models.TextField(_("vote-code"), null=True, blank=True, default=None)
    vote_code_hash = models.TextField(_("vote-code hash"), null=True, blank=True, default=None)
    commitment = JSONField(_("commitment"))
    decommitment = JSONField(_("decommitment"), null=True, blank=True, default=None)
    zk1 = JSONField(_("zero-knowledge proof ZK1"))
    zk2 = JSONField(_("zero-knowledge proof ZK2"), null=True, blank=True, default=None)
    is_voted = models.BooleanField(_("is voted"), default=False)

    objects = BallotOptionManager()

    def generate_decommitment(self):
        if self.part.is_cast:
            self.decommitment = None
        else:
            partial_decommitments = self.partial_decommitments.values_list('value', flat=True)
            self.decommitment = crypto.add_decom(partial_decommitments.iterator())

    def generate_zk2(self):
        if self.part.is_cast:
            pass  # FIXME
        else:
            self.zk2 = None

    def restore_election_option(self):
        if self.part.is_cast:
            self.election_option = None
        else:
            plaintexts = crypto.extract(self.election.commitment_key, self.commitment, self.decommitment, 1)
            try:
                non_blank_index = plaintexts.index(1)
            except ValueError:
                self.election_option = None  # blank option
            else:
                non_blank_election_options = self.election_question.options.exclude(Q(name__isnull=True) | Q(name=''))
                self.election_option = non_blank_election_options[non_blank_index]


class Administrator(BaseAdministrator):
    pass


class Trustee(BaseTrustee):
    @cached_property
    def has_submitted_tally_decommitment(self):
        return self.partial_tally_decommitments.filter(election_question__in=self.election.questions.all()).exists()

    @cached_property
    def has_submitted_all_ballots(self):
        total_ballots = self.election.ballots.filter(parts__is_cast=True).distinct()
        submitted_ballots = total_ballots.filter(parts__questions__partial_zk2__trustee=self).distinct()
        return total_ballots.count() == submitted_ballots.count()

    def send_tally_notification_mail(self, connection=None):
        template_prefix = 'bulletin_board/emails/trustee_tally_notification'
        tally_url_path = reverse('bulletin-board:tally', kwargs={'slug': self.election.slug})
        context = {
            'election': self.election,
            'tally_url': urljoin(settings.DEMOS_VOTING_URLS['bulletin_board'], tally_url_path),
        }
        return self.send_mail(template_prefix, context, connection=connection)


class Voter(BaseVoter):
    def send_election_results_mail(self, connection=None):
        template_prefix = 'bulletin_board/emails/voter_election_results'
        results_url_path = reverse('bulletin-board:election-detail', kwargs={'slug': self.election.slug})
        context = {
            'election': self.election,
            'results_url': urljoin(settings.DEMOS_VOTING_URLS['bulletin_board'], results_url_path),
        }
        return self.send_mail(template_prefix, context, connection=connection)


class PartialTallyDecommitment(models.Model):
    trustee = models.ForeignKey('Trustee', on_delete=models.CASCADE)
    election_question = models.ForeignKey('ElectionQuestion', on_delete=models.CASCADE)
    value = JSONField()

    class Meta:
        default_related_name = 'partial_tally_decommitments'
        unique_together = ['trustee', 'election_question']
        verbose_name = _("partial tally decommitment")
        verbose_name_plural = _("partial tally decommitments")


class PartialDecommitment(models.Model):
    trustee = models.ForeignKey('Trustee', on_delete=models.CASCADE)
    ballot_option = models.ForeignKey('BallotOption', on_delete=models.CASCADE)
    value = JSONField()

    class Meta:
        default_related_name = 'partial_decommitments'
        unique_together = ['trustee', 'ballot_option']
        verbose_name = _("partial decommitment")
        verbose_name_plural = _("partial decommitments")


class PartialQuestionZK2(models.Model):
    trustee = models.ForeignKey('Trustee', on_delete=models.CASCADE, related_name='partial_question_zk2')
    ballot_question = models.ForeignKey('BallotQuestion', on_delete=models.CASCADE)
    value = JSONField()

    class Meta:
        default_related_name = 'partial_zk2'
        unique_together = ['trustee', 'ballot_question']
        verbose_name = _("partial zero-knowledge proof ZK2")
        verbose_name_plural = _("partial zero-knowledge proofs ZK2")


class PartialOptionZK2(models.Model):
    trustee = models.ForeignKey('Trustee', on_delete=models.CASCADE, related_name='partial_option_zk2')
    ballot_option = models.ForeignKey('BallotOption', on_delete=models.CASCADE)
    value = JSONField()

    class Meta:
        default_related_name = 'partial_zk2'
        unique_together = ['trustee', 'ballot_option']
        verbose_name = _("partial zero-knowledge proof ZK2")
        verbose_name_plural = _("partial zero-knowledge proofs ZK2")
