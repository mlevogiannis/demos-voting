from __future__ import absolute_import, division, print_function, unicode_literals

from django import http
from django.db.models import Case, Count, F, OuterRef, Prefetch, Q, Subquery, When, prefetch_related_objects
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.functional import cached_property
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from rest_framework import status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import detail_route
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import APIRootView as BaseAPIRootView
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from demos_voting.base.authentication import HTTPSignatureAuthentication
from demos_voting.base.views import PermissionRequiredMixin, SelectForUpdateMixin
from demos_voting.bulletin_board.forms import TallyForm, UpdateElectionForm
from demos_voting.bulletin_board.models import (
    Ballot, BallotOption, BallotQuestion, Election, ElectionOption,
)
from demos_voting.bulletin_board.pagination import LimitOffsetPagination
from demos_voting.bulletin_board.permissions import (
    CanCreateBallot, CanCreateElection, CanCreateTrustee, CanCreateVoter, CanUpdateBallot, CanUpdateElection,
    CanViewBallot, CanViewElection, DenyAll,
)
from demos_voting.bulletin_board.renderers import BrowsableAPIRenderer, JSONRenderer
from demos_voting.bulletin_board.serializers import (
    BallotSerializer, CreateBallotSerializer, CreateElectionSerializer, CreateTrusteeSerializer, CreateVoterSerializer,
    ElectionSerializer, UpdateBallotSerializer, UpdateElectionSerializer,
)
from demos_voting.bulletin_board.utils.query_params import parse_fields_qs


class HomeView(TemplateView):
    template_name = 'bulletin_board/home.html'


class ElectionListView(ListView):
    model = Election
    paginate_by = 10
    ordering = '-created_at'

    def get_queryset(self):
        user = self.request.user
        q = Q(visibility=Election.VISIBILITY_PUBLIC)
        if user.is_authenticated:
            q |= Q(administrators__user=user) | Q(trustees__user=user) | Q(voters__user=user)
        return super(ElectionListView, self).get_queryset().filter(q).distinct()


class ElectionDetailView(PermissionRequiredMixin, DetailView):
    model = Election
    permission_required = 'bulletin_board.can_view_election'

    def get_object(self, queryset=None):
        election = super(ElectionDetailView, self).get_object(queryset=queryset)
        option_queryset = ElectionOption.objects.all()
        if election.type == election.TYPE_PARTY_CANDIDATE:
            # Annotate the candidate options with the corresponding party's
            # index.
            election_questions = election.questions.annotate(option_count=Count('options'))
            party_count, candidate_count = election_questions.values_list('option_count', flat=True)
            self.candidate_count_per_party = candidate_count // party_count
            option_queryset = option_queryset.annotate(
                party_index=Case(
                    When(
                        question__index=1,
                        then=F('index') / self.candidate_count_per_party,
                    ),
                ),
            )
            # Annotate the candidate options with the corresponding party's
            # vote count.
            option_queryset = option_queryset.annotate(
                party_vote_count=Case(
                    When(
                        question__index=1,
                        then=Subquery(
                            ElectionOption.objects.filter(
                                question__election__pk=OuterRef('question__election_id'),
                                question__index=0,
                                index=(OuterRef('party_index'))
                            ).values('vote_count')[:1]
                        ),
                    ),
                ),
            )
            # Order the options by vote count and then by index. Candidate
            # options are first ordered by their corresponding party.
            option_queryset = option_queryset.order_by(
                F('party_vote_count').desc(nulls_last=True),
                'party_index',
                F('vote_count').desc(nulls_last=True),
                'index',
            )
        prefetch_related_objects([election], Prefetch('questions__options', queryset=option_queryset))
        return election

    def get_context_data(self, **kwargs):
        context = super(ElectionDetailView, self).get_context_data(**kwargs)
        election = self.object
        if election.state == election.STATE_COMPLETED:
            if election.type == election.TYPE_PARTY_CANDIDATE:
                context['candidate_count_per_party'] = self.candidate_count_per_party
                # The number of blank votes cannot be counted, only inferred.
                cast_ballot_count = election.ballots.filter(parts__is_cast=True).count()
                party_question = election.questions.all()[0]
                party_vote_count_sum = sum(o.vote_count for o in party_question.options.all() if not o.is_blank)
                context['blank_party_vote_count'] = cast_ballot_count - party_vote_count_sum
        return context


class ElectionUpdateView(SelectForUpdateMixin, PermissionRequiredMixin, UpdateView):
    form_class = UpdateElectionForm
    model = Election
    permission_required = 'bulletin_board.can_edit_election'
    template_name_suffix = '_update'

    def get_success_url(self):
        return reverse('bulletin-board:election-update', kwargs={'slug': self.object.slug})


class BallotDetailView(PermissionRequiredMixin, DetailView):
    model = Ballot
    permission_required = 'bulletin_board.can_view_election'
    slug_field = 'serial_number'
    slug_url_kwarg = 'serial_number'

    @cached_property
    def election(self):
        return get_object_or_404(Election.objects.all(), slug=self.kwargs.get('slug'))

    def get_permission_object(self):
        return self.election

    def get_queryset(self):
        # Prefetch the option objects.
        option_queryset = BallotOption.objects.prefetch_related('election_option__question__election')
        if self.election.type == self.election.TYPE_QUESTION_OPTION:
            # Order the options by their original index (if available) or their
            # current index.
            option_queryset = option_queryset.order_by('election_option__index', 'index')
        elif self.election.type == self.election.TYPE_PARTY_CANDIDATE:
            # Annotate the candidate options with the corresponding party's
            # ballot index (shuffled).
            election_questions = self.election.questions.annotate(option_count=Count('options'))
            party_option_count, candidate_option_count = election_questions.values_list('option_count', flat=True)
            candidate_count_per_party = candidate_option_count // party_option_count
            option_queryset = option_queryset.annotate(
                party_ballot_option_index=Case(
                    When(
                        question__part__is_cast=False,
                        question__election_question__index=1,
                        then=F('index') / candidate_count_per_party,
                    ),
                ),
            )
            # Annotate the candidate options with the corresponding party's
            # election index (unshuffled).
            option_queryset = option_queryset.annotate(
                party_election_option_index=Case(
                    When(
                        question__part__is_cast=False,
                        question__election_question__index=1,
                        then=Subquery(
                            BallotOption.objects.filter(
                                question__part__pk=OuterRef('question__part_id'),
                                question__election_question__index=0,
                                index=(OuterRef('party_ballot_option_index'))
                            ).values('election_option__index')[:1]
                        ),
                    ),
                ),
            )
            # Order the options by their original index (if available) or their
            # current index. Candidate option are first ordered by party.
            option_queryset = option_queryset.order_by(
                'party_election_option_index',
                'election_option__index',
                'index',
            )
        # Prefetch the question objects.
        question_queryset = BallotQuestion.objects.prefetch_related('election_question__election')
        question_queryset = question_queryset.prefetch_related(Prefetch('options', queryset=option_queryset))
        # Prefetch the part objects.
        queryset = super(BallotDetailView, self).get_queryset().filter(election_id=self.election.pk)
        queryset = queryset.prefetch_related(Prefetch('parts__questions', queryset=question_queryset))
        return queryset

    def get_context_data(self, **kwargs):
        context = super(BallotDetailView, self).get_context_data(**kwargs)
        context['election'] = self.election
        context['ballot_is_cast'] = any(ballot_part.is_cast for ballot_part in self.object.parts.all())
        return context


class TallyView(PermissionRequiredMixin, DetailView):
    form_class = TallyForm
    model = Election
    permission_required = 'bulletin_board.can_tally_election'
    template_name = 'bulletin_board/tally.html'

    def get_context_data(self, **kwargs):
        context = super(TallyView, self).get_context_data(**kwargs)
        context['trustee'] = self.object.trustees.get(user=self.request.user)
        context['cast_ballot_count'] = self.object.ballots.filter(parts__is_cast=True).distinct().count()
        return context


class ElectionCertificateDownloadView(PermissionRequiredMixin, SingleObjectMixin, View):
    model = Election
    permission_required = 'bulletin_board.can_view_election'

    def get(self, request, *args, **kwargs):
        election = self.get_object(self.get_queryset().only('certificate_file'))
        if not election.certificate_file:
            return http.HttpResponseNotFound()
        response = http.FileResponse(election.certificate_file)
        response['Content-Disposition'] = 'attachment; filename="certificate.pem"'
        return response


# API Views ###################################################################

class DynamicFieldsMixin(object):
    def initial(self, request, *args, **kwargs):
        super(DynamicFieldsMixin, self).initial(request, *args, **kwargs)
        if self.action in ('retrieve', 'list'):
            fields_qs = request.query_params.get('fields')
            self._fields = parse_fields_qs(fields_qs, self.get_serializer_class()) if fields_qs else None

    def get_serializer(self, *args, **kwargs):
        if self.action in ('retrieve', 'list'):
            kwargs['fields'] = self._fields
        return super(DynamicFieldsMixin, self).get_serializer(*args, **kwargs)


class ElectionViewSet(DynamicFieldsMixin, SelectForUpdateMixin, ListModelMixin, RetrieveModelMixin, CreateModelMixin,
                      UpdateModelMixin, GenericViewSet):
    lookup_field = 'slug'
    lookup_value_regex = r'[-\w]+'
    queryset = Election.objects.all()
    authentication_classes = (HTTPSignatureAuthentication, SessionAuthentication, TokenAuthentication)
    permission_classes = (DenyAll,)
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer, BrowsableAPIRenderer)
    pagination_class = LimitOffsetPagination
    metadata_class = None
    ordering_fields = ('created_at',)

    def get_queryset(self):
        queryset = super(ElectionViewSet, self).get_queryset()
        queryset = queryset.prefetch_related('questions__options')
        user = self.request.user
        # System users must be able to access all elections.
        system_permissions = ('base.is_ballot_distributor', 'base.is_election_authority', 'base.is_vote_collector')
        if any(user.has_perm(permission) for permission in system_permissions):
            return queryset
        # Normal users can access public or hidden elections and elections in
        # which they participate.
        q = Q(visibility=Election.VISIBILITY_PUBLIC)
        if self.action == 'retrieve':
            # Hidden elections must not appear in the public election list, but
            # they must be accessible if the user knows their URLs.
            q |= Q(visibility=Election.VISIBILITY_HIDDEN)
        if user.is_authenticated:
            # Do a subquery to avoid distinct on the main query (distinct
            # cannot be used with select for update).
            user_q = Q(administrators__user=user) | Q(trustees__user=user) | Q(voters__user=user)
            q |= Q(pk__in=Election.objects.filter(user_q).distinct())
        return queryset.filter(q)

    def get_permissions(self):
        permission_classes = None
        if self.action in ('retrieve', 'list'):
            permission_classes = [CanViewElection]
        elif self.action == 'create':
            permission_classes = [CanCreateElection]
        elif self.action in ('update', 'partial_update'):
            permission_classes = [CanUpdateElection]
        if permission_classes is not None:
            return [permission() for permission in permission_classes]
        return super(ElectionViewSet, self).get_permissions()

    def get_serializer_class(self):
        if self.action in ('retrieve', 'list', 'metadata'):
            return ElectionSerializer
        elif self.action == 'create':
            return CreateElectionSerializer
        elif self.action in ('update', 'partial_update'):
            return UpdateElectionSerializer

    @detail_route(methods=('post',), url_path='trustees', permission_classes=[CanCreateTrustee])
    def create_trustee(self, request, slug=None):
        serializer = CreateTrusteeSerializer(
            data=request.data,
            context={'election': self.get_object()},
            many=isinstance(request.data, list),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED)

    @detail_route(methods=('post',), url_path='voters', permission_classes=[CanCreateVoter])
    def create_voter(self, request, slug=None):
        serializer = CreateVoterSerializer(
            data=request.data,
            context={'election': self.get_object()},
            many=isinstance(request.data, list),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED)


class BallotViewSet(DynamicFieldsMixin, SelectForUpdateMixin, ListModelMixin, RetrieveModelMixin, CreateModelMixin,
                    UpdateModelMixin, GenericViewSet):
    lookup_field = 'serial_number'
    lookup_value_regex = r'[0-9]+'
    queryset = Ballot.objects.all()
    authentication_classes = (HTTPSignatureAuthentication, SessionAuthentication, TokenAuthentication)
    permission_classes = (DenyAll,)
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer, BrowsableAPIRenderer)
    pagination_class = LimitOffsetPagination
    metadata_class = None
    ordering_fields = ('serial_number',)

    def initial(self, request, *args, **kwargs):
        election_queryset = Election.objects.all()
        if self.select_for_update:
            election_queryset = election_queryset.select_for_update()
        self.election = get_object_or_404(election_queryset, slug=self.kwargs.get('election_slug'))
        super(BallotViewSet, self).initial(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(BallotViewSet, self).get_queryset().filter(election_id=self.election.pk)
        queryset = queryset.prefetch_related('parts__questions__options')
        if self.action == 'list':
            # A simple filter to retrieve only the ballots that have been cast.
            is_cast = self.request.query_params.get('is_cast', '')
            if is_cast.lower() == 'true':
                sub_queryset = queryset.filter(parts__is_cast=True).distinct()
                queryset = Ballot.objects.filter(pk__in=sub_queryset)
        return queryset

    def get_permissions(self):
        permission_classes = None
        if self.action in ('retrieve', 'list'):
            permission_classes = [CanViewBallot]
        elif self.action == 'create':
            permission_classes = [CanCreateBallot]
        elif self.action in ('update', 'partial_update'):
            permission_classes = [CanUpdateBallot]
        if permission_classes is not None:
            return [permission() for permission in permission_classes]
        return super(BallotViewSet, self).get_permissions()

    def get_serializer_class(self):
        if self.action in ('retrieve', 'list'):
            return BallotSerializer
        elif self.action == 'create':
            return CreateBallotSerializer
        elif self.action in ('update', 'partial_update'):
            return UpdateBallotSerializer

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
    renderer_classes = (JSONRenderer, BrowsableAPIRenderer)
    metadata_class = None

    def get_view_name(self):
        return super(APIRootView, self).get_view_name().replace('Api', 'API')


class APITestView(APIView):
    authentication_classes = (HTTPSignatureAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer, BrowsableAPIRenderer)
    metadata_class = None

    def get(self, request, *args, **kwargs):
        return Response(data=None)

    def post(self, request, *args, **kwargs):
        return Response(data=request.data)
