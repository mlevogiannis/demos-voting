from __future__ import absolute_import, division, print_function, unicode_literals

import contextlib
import datetime
import re

import pytz

from allauth.account.models import EmailAddress

from celery.result import result_from_tuple

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.mail import EmailMultiAlternatives
from django.core.validators import MinValueValidator
from django.db import models
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils import timezone, translation
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from six.moves.urllib.parse import urljoin

from demos_voting.base.fields import JSONField
from demos_voting.base.utils import base32


# Base models #################################################################

def election_certificate_path(election, filename):
    return "%s/elections/%s/certificate.pem" % (election._meta.app_label, election.slug)


@python_2_unicode_compatible
class BaseElection(models.Model):
    TYPE_QUESTION_OPTION = 'question_option'
    TYPE_PARTY_CANDIDATE = 'party_candidate'
    TYPE_CHOICES = (
        (TYPE_QUESTION_OPTION, _("Question-Option")),
        (TYPE_PARTY_CANDIDATE, _("Party-Candidate")),
    )

    VOTE_CODE_TYPE_SHORT = 'short'
    VOTE_CODE_TYPE_LONG = 'long'
    VOTE_CODE_TYPE_CHOICES = (
        (VOTE_CODE_TYPE_SHORT, _("Short")),
        (VOTE_CODE_TYPE_LONG, _("Long")),
    )

    VISIBILITY_PUBLIC = 'public'
    VISIBILITY_HIDDEN = 'hidden'
    VISIBILITY_PRIVATE = 'private'
    VISIBILITY_CHOICES = (
        (VISIBILITY_PUBLIC, _("Public")),
        (VISIBILITY_HIDDEN, _("Hidden")),
        (VISIBILITY_PRIVATE, _("Private")),
    )

    STATE_SETUP = 'setup'
    STATE_BALLOT_DISTRIBUTION = 'ballot_distribution'
    STATE_VOTING = 'voting'
    STATE_TALLY = 'tally'
    STATE_COMPLETED = 'completed'
    STATE_FAILED = 'failed'
    STATE_CANCELLED = 'cancelled'

    CREDENTIAL_LENGTH = 16  # 80 bits, base32-encoded
    SECURITY_CODE_MAX_LENGTH = 8  # includes a check digit, base10-encoded
    LONG_VOTE_CODE_LENGTH = 16  # 80 bits, base32-encoded
    RECEIPT_LENGTH = 8  # 40 bits, base32-encoded

    slug = models.SlugField(_("identifier"), allow_unicode=True, unique=True)
    name = models.TextField(_("name"))
    voting_starts_at = models.DateTimeField(_("voting starts at"))
    voting_ends_at = models.DateTimeField(_("voting ends at"))
    type = models.CharField(
        _("type"),
        max_length=32,
        choices=TYPE_CHOICES,
        default=TYPE_QUESTION_OPTION,
    )
    vote_code_type = models.CharField(
        _("vote-code type"),
        max_length=32,
        choices=VOTE_CODE_TYPE_CHOICES,
        default=VOTE_CODE_TYPE_SHORT,
    )
    visibility = models.CharField(
        _("visibility"),
        max_length=32,
        choices=VISIBILITY_CHOICES,
        default=VISIBILITY_PUBLIC,
    )
    communication_language = models.CharField(
        _("communication language"),
        max_length=8,
        choices=settings.LANGUAGES,
    )
    ballot_count = models.PositiveIntegerField(
        _("number of ballots"),
        validators=[MinValueValidator(1)],
    )
    credential_length = models.PositiveSmallIntegerField(
        _("credential length"),
        default=CREDENTIAL_LENGTH,
        validators=[MinValueValidator(1)],
    )
    security_code_length = models.PositiveSmallIntegerField(
        _("security code length"),
        null=True,
        blank=True,
        default=None,
        validators=[MinValueValidator(2)],
    )
    vote_code_length = models.PositiveSmallIntegerField(
        _("vote-code length"),
        null=True,
        blank=True,
        default=None,
        validators=[MinValueValidator(1)],
    )
    receipt_length = models.PositiveSmallIntegerField(
        _("receipt length"),
        default=RECEIPT_LENGTH,
        validators=[MinValueValidator(1)],
    )
    commitment_key = models.TextField(_("commitment key"))
    certificate_file = models.FileField(_("certificate"), upload_to=election_certificate_path, null=True, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        abstract = True
        default_related_name = 'elections'
        verbose_name = _("election")
        verbose_name_plural = _("elections")

    def __str__(self):
        return "%s" % self.slug

    def save(self, *args, **kwargs):
        super(BaseElection, self).save(*args, **kwargs)
        # Check if the state has changed and send the appropriate signal.
        update_fields = kwargs.get('update_fields')
        if (update_fields is None or 'state' in update_fields) and 'state' not in self.get_deferred_fields():
            loaded_values = getattr(self, '_loaded_values', None)
            assert not loaded_values or 'state' in self._loaded_values
            old_state = loaded_values.get('state') if loaded_values else None
            new_state = self.state
            if new_state != old_state:
                if new_state == self.STATE_SETUP:
                    from demos_voting.base.signals import setup_started
                    setup_started.send(sender=self.__class__, election=self)
                elif new_state == self.STATE_BALLOT_DISTRIBUTION:
                    from demos_voting.base.signals import ballot_distribution_started
                    ballot_distribution_started.send(sender=self.__class__, election=self)
                elif new_state == self.STATE_VOTING:
                    from demos_voting.base.signals import voting_started
                    voting_started.send(sender=self.__class__, election=self)
                elif new_state == self.STATE_TALLY:
                    from demos_voting.base.signals import tally_started
                    tally_started.send(sender=self.__class__, election=self)
                elif new_state in (self.STATE_COMPLETED, self.STATE_FAILED, self.STATE_CANCELLED):
                    if old_state == self.STATE_SETUP:
                        from demos_voting.base.signals import setup_ended
                        setup_ended.send(sender=self.__class__, election=self)
                    elif old_state == self.STATE_BALLOT_DISTRIBUTION:
                        from demos_voting.base.signals import ballot_distribution_ended
                        ballot_distribution_ended.send(sender=self.__class__, election=self)
                    elif old_state == self.STATE_VOTING:
                        from demos_voting.base.signals import voting_ended
                        voting_ended.send(sender=self.__class__, election=self)
                    elif old_state == self.STATE_TALLY:
                        from demos_voting.base.signals import tally_ended
                        tally_ended.send(sender=self.__class__, election=self)

    @classmethod
    def from_db(cls, db, field_names, values):
        # Save the initial values of the fields that are loaded from the db.
        instance = super(BaseElection, cls).from_db(db, field_names, values)
        instance._loaded_values = dict(zip(field_names, values))
        return instance

    @cached_property
    def question_count(self):
        return self.questions.count()

    @property
    def certificate(self):
        if not hasattr(self, '_certificate'):
            if not self.certificate_file:
                return None
            else:
                self._certificate = x509.load_pem_x509_certificate(
                    data=self.certificate_file.read(),
                    backend=default_backend(),
                )
        return self._certificate

    @cached_property
    def ballot_distributor_url(self):
        return urljoin(settings.DEMOS_VOTING_URLS['ballot_distributor'], 'elections/%s/' % self.slug)

    @cached_property
    def bulletin_board_url(self):
        return urljoin(settings.DEMOS_VOTING_URLS['bulletin_board'], 'elections/%s/' % self.slug)

    @cached_property
    def election_authority_url(self):
        return urljoin(settings.DEMOS_VOTING_URLS['election_authority'], 'elections/%s/' % self.slug)

    @cached_property
    def vote_collector_url(self):
        return urljoin(settings.DEMOS_VOTING_URLS['vote_collector'], 'elections/%s/' % self.slug)


@python_2_unicode_compatible
class BaseElectionQuestion(models.Model):
    OPTION_TABLE_LAYOUT_1_COLUMN = '1_column'
    OPTION_TABLE_LAYOUT_2_COLUMN = '2_column'
    OPTION_TABLE_LAYOUT_CHOICES = (
        (OPTION_TABLE_LAYOUT_1_COLUMN, _("1-column")),
        (OPTION_TABLE_LAYOUT_2_COLUMN, _("2-column")),
    )

    election = models.ForeignKey('Election', on_delete=models.CASCADE)
    index = models.PositiveSmallIntegerField(_("index"), validators=[MinValueValidator(0)])
    name = models.TextField(_("name"), null=True, blank=True)
    min_selection_count = models.PositiveSmallIntegerField(
        _("minimum number of selections"),
        validators=[MinValueValidator(0)],
    )
    max_selection_count = models.PositiveSmallIntegerField(
        _("maximum number of selections"),
        validators=[MinValueValidator(1)],
    )
    option_table_layout = models.CharField(
        _("option table layout"),
        max_length=32,
        choices=OPTION_TABLE_LAYOUT_CHOICES,
        default=OPTION_TABLE_LAYOUT_1_COLUMN,
    )

    class Meta:
        abstract = True
        default_related_name = 'questions'
        ordering = ['index']
        unique_together = ['election', 'index']
        verbose_name = _("question")
        verbose_name_plural = _("questions")

    def __str__(self):
        return "%s" % self.index

    @cached_property
    def option_count(self):
        return self.options.count()

    @cached_property
    def blank_option_count(self):
        return self.options.filter(name=None).count()

    def get_name_display(self):
        if self.election.type == self.election.TYPE_QUESTION_OPTION:
            return self.name
        elif self.election.type == self.election.TYPE_PARTY_CANDIDATE:
            if self.index == 0:
                return _("Select party")
            elif self.index == 1:
                return _("Select candidates")


@python_2_unicode_compatible
class BaseElectionOption(models.Model):
    question = models.ForeignKey('ElectionQuestion', on_delete=models.CASCADE)
    index = models.PositiveSmallIntegerField(_("index"), validators=[MinValueValidator(0)])
    name = models.TextField(_("name"), null=True, blank=True)

    class Meta:
        abstract = True
        default_related_name = 'options'
        ordering = ['index']
        unique_together = ['question', 'index']
        verbose_name = _("option")
        verbose_name_plural = _("options")

    def __str__(self):
        return "%s" % self.index

    @cached_property
    def election(self):
        return self.question.election

    @cached_property
    def is_blank(self):
        return not self.name

    def get_name_display(self):
        if self.election.type == self.election.TYPE_QUESTION_OPTION:
            return self.name
        elif self.election.type == self.election.TYPE_PARTY_CANDIDATE:
            return self.name or _("Blank")


@python_2_unicode_compatible
class BaseBallot(models.Model):
    election = models.ForeignKey('Election', on_delete=models.CASCADE)
    serial_number = models.PositiveIntegerField(_("serial number"), validators=[MinValueValidator(100)])

    class Meta:
        abstract = True
        default_related_name = 'ballots'
        ordering = ['serial_number']
        unique_together = ['election', 'serial_number']
        verbose_name = _("ballot")
        verbose_name_plural = _("ballots")

    def __str__(self):
        return "%s" % self.serial_number


@python_2_unicode_compatible
class BaseBallotPart(models.Model):
    TAG_A = 'A'
    TAG_B = 'B'
    TAG_CHOICES = (
        (TAG_A, 'A'),
        (TAG_B, 'B'),
    )

    ballot = models.ForeignKey('Ballot', on_delete=models.CASCADE)
    tag = models.CharField(_("tag"), max_length=1, choices=TAG_CHOICES)

    class Meta:
        abstract = True
        default_related_name = 'parts'
        ordering = ['tag']
        unique_together = ['ballot', 'tag']
        verbose_name = _("part")
        verbose_name_plural = _("parts")

    def __str__(self):
        return "%s" % self.tag

    @cached_property
    def election(self):
        return self.ballot.election

    def get_credential_display(self):
        return base32.hyphenate(self.credential, 4)

    @property
    def voting_booth_url(self):
        if self.election.vote_code_type == self.election.VOTE_CODE_TYPE_SHORT:
            url_path = 'elections/%(slug)s/voting-booth/%(serial_number)d/%(tag)s/%(credential)s/'
        elif self.election.vote_code_type == self.election.VOTE_CODE_TYPE_LONG:
            url_path = 'elections/%(slug)s/voting-booth/%(serial_number)d/%(tag)s/'
        return urljoin(settings.DEMOS_VOTING_URLS['vote_collector'], url_path % {
            'slug': self.election.slug,
            'serial_number': self.ballot.serial_number,
            'tag': self.tag,
            'credential': self.credential,
        })


@python_2_unicode_compatible
class BaseBallotQuestion(models.Model):
    part = models.ForeignKey('BallotPart', on_delete=models.CASCADE)
    election_question = models.ForeignKey(
        'ElectionQuestion',
        on_delete=models.CASCADE,
        related_name='ballot_questions',
    )

    class Meta:
        abstract = True
        default_related_name = 'questions'
        ordering = ['election_question']
        unique_together = ['part', 'election_question']
        verbose_name = _("question")
        verbose_name_plural = _("questions")

    def __str__(self):
        return "%s" % self.election_question.index

    @cached_property
    def election(self):
        return self.ballot.election

    @cached_property
    def ballot(self):
        return self.part.ballot


@python_2_unicode_compatible
class BaseBallotOption(models.Model):
    question = models.ForeignKey('BallotQuestion', on_delete=models.CASCADE)
    index = models.PositiveSmallIntegerField(_("index"), validators=[MinValueValidator(0)])
    receipt = models.TextField(_("receipt"))

    class Meta:
        abstract = True
        default_related_name = 'options'
        ordering = ['index']
        unique_together = ['question', 'index']
        verbose_name = _("option")
        verbose_name_plural = _("options")

    def __str__(self):
        return "%s" % self.index

    @cached_property
    def election(self):
        return self.ballot.election

    @cached_property
    def ballot(self):
        return self.part.ballot

    @cached_property
    def part(self):
        return self.question.part

    @cached_property
    def election_question(self):
        return self.question.election_question

    def get_vote_code_display(self):
        if self.election.vote_code_type == self.election.VOTE_CODE_TYPE_SHORT:
            return self.vote_code
        elif self.election.vote_code_type == self.election.VOTE_CODE_TYPE_LONG:
            return base32.hyphenate(self.vote_code, 4)

    def get_receipt_display(self):
        return self.receipt[-self.election.receipt_length:]


@python_2_unicode_compatible
class BaseElectionUser(models.Model):
    election = models.ForeignKey('Election', on_delete=models.CASCADE)

    # If an election user instance is created with a user but without an email
    # address then it is permanently tied to that user and an email address
    # must never be added. If the instance is created with an email address
    # then the user will be automatically populated when a user with this email
    # addresses signs up/in. In general, either the user or the email address
    # must be specified when creating a new instance. Warning: a single user
    # might end up with multiple administrator/trustee/voter accounts if they
    # have multiple valid email addresses.

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    email = models.EmailField(_("email address"), null=True, blank=True)

    class Meta:
        abstract = True
        unique_together = ['election', 'user', 'email']

    def __str__(self):
        return self.get_display_name()

    def save(self, *args, **kwargs):
        assert self.email or self.user
        if self.email:
            try:
                email_address = EmailAddress.objects.only('user', 'verified').get(email__iexact=self.email)
            except EmailAddress.DoesNotExist:
                self.user = None
            else:
                self.user = email_address.user if email_address.verified else None
        return super(BaseElectionUser, self).save(*args, **kwargs)

    def get_display_name(self):
        return (self.user.get_full_name() if self.user else None) or self.get_email()

    def get_email(self):
        return self.email or self.user.email

    def send_mail(self, template_prefix, context, attachments=None, connection=None, render_only=False):
        context.update({
            'user_display_name': self.get_display_name(),
            'user_email': self.get_email(),
            'site_name': settings.DEMOS_VOTING_SITE_NAME,
        })

        def render_mail():
            subject = render_to_string('%s_subject.txt' % template_prefix, context).strip()
            body = re.sub(r'\n{3,}', '\n\n', render_to_string('%s_body.txt' % template_prefix, context)).strip()
            try:
                html_body = render_to_string('%s_body.html' % template_prefix, context).strip()
            except TemplateDoesNotExist:
                html_body = None
            return subject, body, html_body

        # Render the message in the user's language and timezone (if
        # available), or in the configured communication language.
        with translation.override(self.election.communication_language):
            if self.user:
                with self.user.profile.override_language_and_timezone():
                    subject, body, html_body = render_mail()
            else:
                subject, body, html_body = render_mail()
        # Construct the message object. HTML body and attachments are optional.
        to = [self.get_email()]
        message = EmailMultiAlternatives(subject, body, to=to, attachments=attachments, connection=connection)
        if html_body:
            message.attach_alternative(html_body, 'text/html')
        # If `render_only` is True then the message is rendered and returned
        # but not sent.
        if not render_only:
            message.send()
        return message


class BaseAdministrator(BaseElectionUser):
    class Meta(BaseElectionUser.Meta):
        abstract = True
        default_related_name = 'administrators'
        verbose_name = _("administrator")
        verbose_name_plural = _("administrators")


class BaseTrustee(BaseElectionUser):
    class Meta(BaseElectionUser.Meta):
        abstract = True
        default_related_name = 'trustees'
        verbose_name = _("trustee")
        verbose_name_plural = _("trustees")


class BaseVoter(BaseElectionUser):
    class Meta(BaseElectionUser.Meta):
        abstract = True
        default_related_name = 'voters'
        verbose_name = _("voter")
        verbose_name_plural = _("voters")


# User models #################################################################

class User(AbstractUser):
    pass


@python_2_unicode_compatible
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_("user"))
    language = models.CharField(
        _("language"),
        max_length=8,
        null=True,
        blank=True,
        choices=settings.LANGUAGES,
        default=None,
    )
    timezone = models.CharField(
        _("time zone"),
        max_length=32,
        null=True,
        blank=True,
        choices=[(timezone_name, timezone_name) for timezone_name in pytz.common_timezones],
        default=None,
    )

    class Meta:
        default_related_name = 'profile'
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")

    def __str__(self):
        return "%s" % self.user

    @contextlib.contextmanager
    def override_language_and_timezone(self):
        if self.language is not None:
            old_language = translation.get_language()
            translation.activate(self.language)
        if self.timezone is not None:
            old_timezone = timezone.get_current_timezone()
            timezone.activate(self.timezone)
        yield  # executes the `with` statement's body
        if self.language is not None:
            translation.activate(old_language)
        if self.timezone is not None:
            timezone.activate(old_timezone)


# HTTP Signature Authentication models ########################################

@python_2_unicode_compatible
class HTTPSignatureKey(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    key_id = models.TextField(_("key id"), unique=True)
    key = models.TextField(_("key"))

    class Meta:
        verbose_name = _("HTTP signature key")
        verbose_name_plural = _("HTTP signature keys")

    def __str__(self):
        return "%s" % self.key_id


@python_2_unicode_compatible
class HTTPSignatureNonce(models.Model):
    MAX_CLOCK_SKEW = datetime.timedelta(seconds=300)

    key = models.ForeignKey('base.HTTPSignatureKey', on_delete=models.CASCADE, related_name='nonces')
    client_id = models.CharField(_("client id"), max_length=39)  # 128-bit, base-10
    nonce = models.CharField(_("nonce"), max_length=10)  # 32-bit, base-10
    date = models.DateTimeField(_("date"))

    class Meta:
        unique_together = ['key', 'client_id', 'nonce', 'date']
        verbose_name = _("HTTP signature nonce")
        verbose_name_plural = _("HTTP signature nonces")

    def __str__(self):
        return "%s" % self.client_id


# Celery task models ##########################################################

@python_2_unicode_compatible
class Task(models.Model):
    name = models.TextField(_("name"))
    result = JSONField(_("result"))
    task_id = models.UUIDField(_("identifier"), unique=True)

    class Meta:
        default_related_name = 'tasks'
        verbose_name = _("task")
        verbose_name_plural = _("tasks")

    def __str__(self):
        return "%s" % self.name

    def save(self, *args, **kwargs):
        self.result = self.result.as_tuple()
        super(Task, self).save(*args, **kwargs)

    @classmethod
    def from_db(cls, *args, **kwargs):
        instance = super(Task, cls).from_db(*args, **kwargs)
        instance.result = result_from_tuple(instance.result)
        return instance
