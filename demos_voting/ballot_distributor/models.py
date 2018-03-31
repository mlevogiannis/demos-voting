from __future__ import absolute_import, division, print_function, unicode_literals

import csv
import os
import uuid
import zipfile

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator, validate_email
from django.db import models
from django.db.models import Sum
from django.urls import reverse
from django.utils import translation
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from demos_voting.base.models import (
    BaseAdministrator, BaseBallot, BaseBallotOption, BaseBallotPart, BaseBallotQuestion, BaseElection,
    BaseElectionOption, BaseElectionQuestion, BaseVoter,
)
from demos_voting.base.utils.pdf import BallotPDF


class Election(BaseElection):
    STATE_CHOICES = (
        (BaseElection.STATE_SETUP, _("Setup")),
        (BaseElection.STATE_BALLOT_DISTRIBUTION, _("Ballot distribution")),
        (BaseElection.STATE_COMPLETED, _("Completed")),
        (BaseElection.STATE_FAILED, _("Failed")),
        (BaseElection.STATE_CANCELLED, _("Cancelled")),
    )

    state = models.CharField(_("state"), max_length=32, choices=STATE_CHOICES, default=BaseElection.STATE_SETUP)
    ballot_distribution_started_at = models.DateTimeField(_("ballot distribution started at"), null=True, blank=True)
    ballot_distribution_ended_at = models.DateTimeField(_("ballot distribution ended at"), null=True, blank=True)

    def get_absolute_url(self):
        return reverse('ballot-distributor:election-detail', args=[self.slug])

    @cached_property
    def remaining_ballot_count(self):
        ballot_archive_ballot_count = self.ballot_archives.aggregate(Sum('ballot_count'))['ballot_count__sum'] or 0
        return self.ballot_count - (self.voters.count() + ballot_archive_ballot_count)

    @cached_property
    def _ballot_pdf(self):
        return BallotPDF(self)


class ElectionQuestion(BaseElectionQuestion):
    pass


class ElectionOption(BaseElectionOption):
    pass


def ballot_file_path(ballot, filename):
    return "ballot_distributor/elections/%s/ballots/%s" % (ballot.election.slug, filename)


class Ballot(BaseBallot):
    voter = models.OneToOneField(
        'Voter',
        on_delete=models.CASCADE,
        related_name='ballot',
        null=True,
        blank=True,
        default=None,
    )
    archive = models.ForeignKey(
        'BallotArchive',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
    )
    file = models.FileField(_("file"), upload_to=ballot_file_path, null=True, blank=True, default=None)

    def generate_file(self, save=True):
        """
        Generate a ballot paper in PDF format.
        """
        language = self.election.communication_language
        if self.voter:
            if self.voter.user:
                language = self.voter.user.profile.language
        elif self.archive:
            language = self.archive.language
        with translation.override(language):
            pdf_file = self.election._ballot_pdf.generate(self)
        self.file.save("%d.pdf" % self.serial_number, ContentFile(pdf_file.getvalue()), save=save)


class BallotPart(BaseBallotPart):
    credential = models.TextField(_("credential"))
    security_code = models.CharField(_("security code"), max_length=32, null=True, blank=True)

    def get_security_code_display(self):
        return self.security_code


class BallotQuestion(BaseBallotQuestion):
    pass


class BallotOption(BaseBallotOption):
    vote_code = models.TextField(_("vote-code"))


class Administrator(BaseAdministrator):
    def send_voter_list_failed_mail(self, voter_list, connection=None):
        template_prefix = 'ballot_distributor/emails/administrator_voter_list_failed'
        context = {'election': self.election, 'voter_list': voter_list}
        return self.send_mail(template_prefix, context, connection=connection)


class Voter(BaseVoter):
    def send_ballot_mail(self, connection=None):
        template_prefix = 'ballot_distributor/emails/voter_ballot'
        context = {'election': self.election, 'ballot': self.ballot}
        attachments = [('%d.pdf' % self.ballot.serial_number, self.ballot.file.read())]
        return self.send_mail(template_prefix, context, attachments, connection=connection)


def ballot_archive_file_path(ballot_archive, filename):
    return "ballot_distributor/elections/%s/ballot_archives/%s" % (ballot_archive.election.slug, filename)


@python_2_unicode_compatible
class BallotArchive(models.Model):
    STATE_PENDING = 'pending'
    STATE_PROCESSING = 'processing'
    STATE_COMPLETED = 'completed'
    STATE_FAILED = 'failed'
    STATE_CANCELLED = 'cancelled'
    STATE_CHOICES = (
        (STATE_PENDING, _("Pending")),
        (STATE_PROCESSING, _("Processing")),
        (STATE_COMPLETED, _("Completed")),
        (STATE_FAILED, _("Failed")),
        (STATE_CANCELLED, _("Cancelled")),
    )

    election = models.ForeignKey('Election', on_delete=models.CASCADE)
    administrator = models.ForeignKey('Administrator', on_delete=models.SET_NULL, null=True)
    ballot_count = models.PositiveIntegerField(_("number of ballots"), validators=[MinValueValidator(1)])
    language = models.CharField(_("language"), max_length=8, choices=settings.LANGUAGES)
    file = models.FileField(_("file"), upload_to=ballot_archive_file_path, null=True, blank=True, default=None)
    state = models.CharField(_("state"), max_length=32, choices=STATE_CHOICES, default=STATE_PENDING)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    processing_started_at = models.DateTimeField(_("processing started at"), null=True, blank=True, default=None)
    processing_ended_at = models.DateTimeField(_("processing ended at"), null=True, blank=True, default=None)
    uuid = models.UUIDField(default=uuid.uuid4)

    class Meta:
        default_related_name = 'ballot_archives'
        ordering = ['created_at']
        unique_together = ['election', 'uuid']
        verbose_name = _("ballot archive")
        verbose_name_plural = _("ballot archives")

    def __str__(self):
        return "%s" % self.uuid

    def generate_file(self, save=True):
        self.file.save("%d.zip" % self.uuid, ContentFile(''), save=save)
        with zipfile.ZipFile(self.file.path, mode='w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zip_file:
            for ballot in self.ballots.iterator():
                zip_file.write(ballot.file.path, os.path.basename(ballot.file.name))


def voter_list_file_path(voter_list, filename):
    return "ballot_distributor/elections/%s/voter_lists/%s" % (voter_list.election.slug, filename)


@python_2_unicode_compatible
class VoterList(models.Model):
    STATE_PENDING = 'pending'
    STATE_PROCESSING = 'processing'
    STATE_COMPLETED = 'completed'
    STATE_FAILED = 'failed'
    STATE_CANCELLED = 'cancelled'
    STATE_CHOICES = (
        (STATE_PENDING, _("Pending")),
        (STATE_PROCESSING, _("Processing")),
        (STATE_COMPLETED, _("Completed")),
        (STATE_FAILED, _("Failed")),
        (STATE_CANCELLED, _("Cancelled")),
    )

    ERROR_INVALID_FILE = 'invalid_file'
    ERROR_EMPTY_FILE = 'empty_file'
    ERROR_TOO_MANY_VALUES = 'too_many_values'
    ERROR_CHOICES = (
        (ERROR_INVALID_FILE, _("The file is not valid.")),
        (ERROR_EMPTY_FILE, _("The file is empty.")),
        (ERROR_TOO_MANY_VALUES, _("The file contains more email addresses than the number of ballots available.")),
    )

    election = models.ForeignKey('Election', on_delete=models.CASCADE)
    administrator = models.ForeignKey('Administrator', on_delete=models.SET_NULL, null=True)
    voters = models.ManyToManyField('Voter')
    file = models.FileField(_("file"), upload_to=voter_list_file_path, null=True, blank=True, default=None)
    state = models.CharField(_("state"), max_length=32, choices=STATE_CHOICES, default=STATE_PENDING)
    error = models.CharField(_("error"), max_length=32, choices=ERROR_CHOICES, null=True, blank=True, default=None)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    processing_started_at = models.DateTimeField(_("processing started at"), null=True, blank=True, default=None)
    processing_ended_at = models.DateTimeField(_("processing ended at"), null=True, blank=True, default=None)

    class Meta:
        default_related_name = 'voter_lists'
        ordering = ['created_at']
        verbose_name = _("voter list")
        verbose_name_plural = _("voter lists")

    def __str__(self):
        return "%s" % (self.file or '-')

    def load_file(self):
        voter_count = 0
        created_voter_count = 0
        try:
            reader = csv.reader(self.file)
            for row in reader:
                if len(row) < 1:
                    continue
                elif len(row) > 1:
                    raise ValidationError(self.ERROR_INVALID_FILE)
                else:
                    email = row[0].strip()
                    try:
                        validate_email(email)
                    except ValidationError:
                        raise ValidationError(self.ERROR_INVALID_FILE)
                    voter, created = self.election.voters.get_or_create(email__iexact=email, defaults={'email': email})
                    if created:
                        created_voter_count += 1
                        if created_voter_count > self.election.remaining_ballot_count:
                            raise ValidationError(self.ERROR_TOO_MANY_VALUES)
                    voter_count += 1
                    self.voters.add(voter)
        except csv.Error:
            raise ValidationError(self.ERROR_INVALID_FILE)
        else:
            if not voter_count:
                raise ValidationError(self.ERROR_EMPTY_FILE)
            return voter_count
