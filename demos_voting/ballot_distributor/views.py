from __future__ import absolute_import, division, print_function, unicode_literals

from django import http
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.functional import cached_property
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import CreateView, UpdateView

from rest_framework.mixins import CreateModelMixin, UpdateModelMixin
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.routers import APIRootView as BaseAPIRootView
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from demos_voting.ballot_distributor.forms import CreateBallotArchiveForm, CreateVoterListForm, UpdateElectionForm
from demos_voting.ballot_distributor.models import Ballot, BallotArchive, Election, VoterList
from demos_voting.ballot_distributor.permissions import CanCreateBallot, CanCreateElection, CanUpdateElection, DenyAll
from demos_voting.ballot_distributor.serializers import (
    CreateBallotSerializer, CreateElectionSerializer, UpdateElectionSerializer,
)
from demos_voting.base.authentication import HTTPSignatureAuthentication
from demos_voting.base.views import PermissionRequiredMixin, SelectForUpdateMixin


class HomeView(TemplateView):
    template_name = 'ballot_distributor/home.html'


class ElectionListView(LoginRequiredMixin, ListView):
    model = Election
    paginate_by = 10
    ordering = '-created_at'

    def get_queryset(self):
        return super(ElectionListView, self).get_queryset().filter(administrators__user=self.request.user)


class ElectionDetailView(PermissionRequiredMixin, DetailView):
    model = Election
    permission_required = 'ballot_distributor.can_view_election'


class ElectionUpdateView(SelectForUpdateMixin, PermissionRequiredMixin, UpdateView):
    form_class = UpdateElectionForm
    model = Election
    permission_required = 'ballot_distributor.can_edit_election'
    template_name_suffix = '_update'

    def get_success_url(self):
        return reverse('ballot-distributor:election-update', kwargs={'slug': self.object.slug})


class BallotArchiveCreateView(SelectForUpdateMixin, PermissionRequiredMixin, CreateView):
    form_class = CreateBallotArchiveForm
    model = BallotArchive
    permission_required = 'ballot_distributor.can_create_ballot_archive'
    template_name = 'ballot_distributor/ballot_archive_create.html'

    @cached_property
    def election(self):
        election_queryset = Election.objects.all()
        if self.select_for_update:
            election_queryset = election_queryset.select_for_update()
        return get_object_or_404(election_queryset, slug=self.kwargs.get('slug'))

    def get_permission_object(self):
        return self.election

    def get_context_data(self, **kwargs):
        context = super(BallotArchiveCreateView, self).get_context_data(**kwargs)
        context['election'] = self.election
        return context

    def get_form_kwargs(self):
        kwargs = super(BallotArchiveCreateView, self).get_form_kwargs()
        kwargs['election'] = self.election
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse('ballot-distributor:election-detail', kwargs={'slug': self.election.slug})


class BallotArchiveFileDownloadView(PermissionRequiredMixin, SingleObjectMixin, View):
    model = BallotArchive
    permission_required = 'ballot_distributor.can_create_ballot_archive'
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    @cached_property
    def election(self):
        return get_object_or_404(Election.objects.all(), slug=self.kwargs.get('slug'))

    def get_permission_object(self):
        return self.election

    def get_queryset(self):
        return super(BallotArchiveFileDownloadView, self).get_queryset().filter(election_id=self.election.pk)

    def get(self, request, *args, **kwargs):
        election = self.election
        ballot_archive = self.get_object()
        if (election.state not in (election.STATE_BALLOT_DISTRIBUTION, election.STATE_COMPLETED) or
                ballot_archive.state != ballot_archive.STATE_COMPLETED or not ballot_archive.file):
            return http.HttpResponseNotFound()
        response = http.FileResponse(ballot_archive.file)
        response['Content-Disposition'] = 'attachment; filename="ballots.zip"'
        return response


class VoterListCreateView(SelectForUpdateMixin, PermissionRequiredMixin, CreateView):
    form_class = CreateVoterListForm
    model = VoterList
    permission_required = 'ballot_distributor.can_create_voter_list'
    template_name = 'ballot_distributor/voter_list_create.html'

    @cached_property
    def election(self):
        election_queryset = Election.objects.all()
        if self.select_for_update:
            election_queryset = election_queryset.select_for_update()
        return get_object_or_404(election_queryset, slug=self.kwargs.get('slug'))

    def get_permission_object(self):
        return self.election

    def get_context_data(self, **kwargs):
        context = super(VoterListCreateView, self).get_context_data(**kwargs)
        context['election'] = self.election
        return context

    def get_form_kwargs(self):
        kwargs = super(VoterListCreateView, self).get_form_kwargs()
        kwargs['election'] = self.election
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse('ballot-distributor:election-detail', kwargs={'slug': self.election.slug})


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
