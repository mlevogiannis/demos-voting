from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import prefetch_related_objects
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import timesince, timeuntil
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.edit import ModelFormMixin, ProcessFormView, UpdateView

from rest_framework.mixins import CreateModelMixin, UpdateModelMixin
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.routers import APIRootView as BaseAPIRootView
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from six.moves.urllib.parse import urljoin

from demos_voting.base.authentication import HTTPSignatureAuthentication
from demos_voting.base.utils import base32, hasher
from demos_voting.base.views import PermissionRequiredMixin, SelectForUpdateMixin
from demos_voting.vote_collector.forms import UpdateElectionForm, VotingBoothBallotPartForm
from demos_voting.vote_collector.models import Ballot, BallotPart, Election
from demos_voting.vote_collector.permissions import CanCreateBallot, CanCreateElection, CanUpdateElection, DenyAll
from demos_voting.vote_collector.serializers import (
    CreateBallotSerializer, CreateElectionSerializer, UpdateElectionSerializer,
)


class HomeView(TemplateView):
    template_name = 'vote_collector/home.html'


class ElectionListView(LoginRequiredMixin, ListView):
    model = Election
    paginate_by = 10
    ordering = '-created_at'

    def get_queryset(self):
        return super(ElectionListView, self).get_queryset().filter(administrators__user=self.request.user)


class ElectionDetailView(PermissionRequiredMixin, DetailView):
    model = Election
    permission_required = 'vote_collector.can_view_election'


class ElectionUpdateView(SelectForUpdateMixin, PermissionRequiredMixin, UpdateView):
    form_class = UpdateElectionForm
    model = Election
    permission_required = 'vote_collector.can_edit_election'
    template_name_suffix = '_update'

    def get_success_url(self):
        return reverse('vote-collector:election-update', kwargs={'slug': self.object.slug})


class QRCodeView(TemplateView):
    template_name = 'vote_collector/qr_code.html'

    def get_context_data(self, **kwargs):
        context = super(QRCodeView, self).get_context_data(**kwargs)
        valid_url_prefixes = [urljoin(settings.DEMOS_VOTING_URLS['vote_collector'], 'elections/')]
        election_list_url = self.request.build_absolute_uri(reverse('vote-collector:election-list'))
        if election_list_url not in valid_url_prefixes:
            valid_url_prefixes.append(election_list_url)
        context['valid_url_prefixes'] = valid_url_prefixes
        return context


class VotingBoothView(TemplateResponseMixin, ModelFormMixin, ProcessFormView):
    model = BallotPart
    form_class = VotingBoothBallotPartForm
    slug_field = 'tag'
    slug_url_kwarg = 'tag'
    template_name = 'vote_collector/voting_booth.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            self._prepare()
        except ValidationError as e:
            return self.render_to_response(self.get_context_data(errors=[e.message]), status=400)
        else:
            return super(VotingBoothView, self).get(request, *args, **kwargs)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # Synchronize on the ballot object (not the part object), before trying
        # to validate and save the submitted vote.
        ballot_queryset = Ballot.objects.only('pk').select_for_update()
        get_object_or_404(ballot_queryset, election__slug=kwargs['slug'], serial_number=kwargs['serial_number'])
        # The ballot object is now locked, continue with the processing of the
        # submitted vote.
        self.object = self.get_object()
        try:
            self._prepare()
        except ValidationError as e:
            return JsonResponse([e.message], safe=False, status=400)
        else:
            return super(VotingBoothView, self).post(request, *args, **kwargs)

    def _prepare(self):
        """
        Validation logic common for both GET and POST requests.
        """
        ballot_part = self.object
        ballot = ballot_part.ballot
        election = ballot.election
        # Get the current time.
        timezone_now = timezone.now()
        # Check the election's state.
        if election.state in (election.STATE_FAILED, election.STATE_CANCELLED):
            raise ValidationError(_("The election was cancelled."))
        if timezone_now < election.voting_starts_at:
            raise ValidationError(
                _("The election starts in %(time_until)s.") % {
                    'time_until': timeuntil(election.voting_starts_at, timezone_now),
                }
            )
        if timezone_now > election.voting_ends_at:
            raise ValidationError(
                _("The election ended %(time_since)s ago.") % {
                    'time_since': timesince(election.voting_ends_at, timezone_now),
                }
            )
        if election.state != election.STATE_VOTING:
            raise ValidationError(_("The election has not started yet. Please try again later."))
        # Validate the credential (if using short vote-codes).
        if election.vote_code_type == election.VOTE_CODE_TYPE_SHORT:
            try:
                credential = self.kwargs.get('credential')
                if not credential:
                    raise ValueError
                credential = base32.normalize(credential)  # raises ValueError
                if not hasher.verify(credential, ballot_part.credential_hash):
                    raise ValueError
            except ValueError:
                raise ValidationError(_("The credential in the URL is not valid."))
            else:
                self.credential = credential
        # Check if either ballot part has already been cast.
        if ballot.parts.filter(is_cast=True).exists():
            raise ValidationError(_("This ballot has already been cast."))
        # Validation successful, prefetch all related objects.
        prefetch_related_objects([ballot_part], 'questions__options')
        prefetch_related_objects([election], 'questions__options')

    def get_queryset(self):
        queryset = super(VotingBoothView, self).get_queryset()
        queryset = queryset.filter(
            ballot__election__slug=self.kwargs['slug'],
            ballot__serial_number=self.kwargs['serial_number'],
        )
        queryset = queryset.select_related('ballot__election')
        return queryset

    def get_form_kwargs(self):
        kwargs = super(VotingBoothView, self).get_form_kwargs()
        kwargs['credential'] = getattr(self, 'credential', None)
        return kwargs

    def form_valid(self, form):
        super(VotingBoothView, self).form_valid(form)
        questions = []
        for option_formset in form.option_formsets:
            question = {}
            for ballot_option in option_formset.ballot_options:
                question[ballot_option.vote_code] = ballot_option.receipt
            questions.append(question)
        return JsonResponse(questions, safe=False)

    def form_invalid(self, form):
        super(VotingBoothView, self).form_invalid(form)
        return JsonResponse(form.non_field_errors(), safe=False, status=400)

    def get_success_url(self):
        return '/'  # this value will not be used, `form_valid` returns a JSON response

    def get_context_data(self, **kwargs):
        context = super(VotingBoothView, self).get_context_data(**kwargs)
        election = self.object.election
        context['election'] = election
        context['ballot_part'] = self.object
        errors = context.setdefault('errors', None)
        if not errors:
            if election.type == election.TYPE_PARTY_CANDIDATE:
                party_option_count = election.questions.all()[0].option_count
                candidate_option_count = election.questions.all()[1].option_count
                context['candidate_count_per_party'] = candidate_option_count // party_option_count
            if election.vote_code_type == election.VOTE_CODE_TYPE_SHORT:
                context['credential'] = self.credential
        return context


class VotingBoothSuccessView(DetailView):
    model = Election
    template_name = 'vote_collector/voting_booth_success.html'


# API Views ###################################################################

class ElectionViewSet(SelectForUpdateMixin, CreateModelMixin, UpdateModelMixin, GenericViewSet):
    lookup_field = 'slug'
    lookup_value_regex = r'[-\w]+'
    queryset = Election.objects.all()
    authentication_classes = (HTTPSignatureAuthentication,)
    permission_classes = (DenyAll,)
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)
    metadata_class = None

    def get_permissions(self):
        permission_classes = None
        if self.action == 'create':
            permission_classes = [CanCreateElection]
        elif self.action in ('update', 'partial_update'):
            permission_classes = [CanUpdateElection]
        if permission_classes is not None:
            return [permission() for permission in permission_classes]
        return super(ElectionViewSet, self).get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateElectionSerializer
        elif self.action in ('update', 'partial_update'):
            return UpdateElectionSerializer


class BallotViewSet(SelectForUpdateMixin, CreateModelMixin, GenericViewSet):
    lookup_field = 'serial_number'
    lookup_value_regex = r'[0-9]+'
    queryset = Ballot.objects.all()
    authentication_classes = (HTTPSignatureAuthentication,)
    permission_classes = (DenyAll,)
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)
    metadata_class = None

    def initial(self, request, *args, **kwargs):
        election_queryset = Election.objects.all()
        if self.select_for_update:
            election_queryset = election_queryset.select_for_update()
        self.election = get_object_or_404(election_queryset, slug=self.kwargs.get('election_slug'))
        super(BallotViewSet, self).initial(request, *args, **kwargs)

    def get_queryset(self):
        return super(BallotViewSet, self).get_queryset().filter(election_id=self.election.pk)

    def get_permissions(self):
        permission_classes = None
        if self.action == 'create':
            permission_classes = [CanCreateBallot]
        if permission_classes is not None:
            return [permission() for permission in permission_classes]
        return super(BallotViewSet, self).get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateBallotSerializer

    def get_serializer_context(self):
        context = super(BallotViewSet, self).get_serializer_context()
        context['election'] = self.election
        return context

    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get('data'), list):
            kwargs['many'] = True
        return super(BallotViewSet, self).get_serializer(*args, **kwargs)


class APIRootView(BaseAPIRootView):
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)
    metadata_class = None


class APITestView(APIView):
    authentication_classes = (HTTPSignatureAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)
    metadata_class = None

    def get(self, request, *args, **kwargs):
        return Response(data=None)

    def post(self, request, *args, **kwargs):
        return Response(data=request.data)
