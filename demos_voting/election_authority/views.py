from __future__ import absolute_import, division, print_function, unicode_literals

import base64

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.encoding import force_text
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.routers import APIRootView as BaseAPIRootView
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from demos_voting.base.authentication import HTTPSignatureAuthentication
from demos_voting.base.views import PermissionRequiredMixin, SelectForUpdateMixin
from demos_voting.election_authority.forms import CreateElectionForm, UpdateElectionForm
from demos_voting.election_authority.models import Ballot, Election
from demos_voting.election_authority.permissions import DenyAll
from demos_voting.election_authority.utils.pdf import generate_sample_ballot_pdf


class HomeView(TemplateView):
    template_name = 'election_authority/home.html'


class ElectionListView(LoginRequiredMixin, ListView):
    model = Election
    paginate_by = 10
    ordering = '-created_at'

    def get_queryset(self):
        return super(ElectionListView, self).get_queryset().filter(administrators__user=self.request.user)


class ElectionDetailView(PermissionRequiredMixin, DetailView):
    model = Election
    permission_required = 'election_authority.can_view_election'

    def get_context_data(self, **kwargs):
        context = super(ElectionDetailView, self).get_context_data(**kwargs)
        election = self.object
        if election.state == election.STATE_SETUP:
            # Calculate the setup's progress.
            group_percent = 0
            try:
                group_task = election.tasks.get(name='generate_ballots_task_group')
            except ObjectDoesNotExist:
                pass
            else:
                group_result = group_task.result
                if group_result.children:
                    for child_result in group_result.children:
                        if child_result.state == 'PROGRESS':
                            if child_result.result:
                                child_percent = child_result.result['current'] / child_result.result['total']
                            else:
                                child_percent = 1
                        elif child_result.state == 'SUCCESS':
                            child_percent = 1
                        else:
                            child_percent = 0
                        group_percent += child_percent * (1 / len(group_result.children))
            context['progress'] = 1 + int(99 * group_percent)
        return context


class ElectionUpdateView(SelectForUpdateMixin, PermissionRequiredMixin, UpdateView):
    form_class = UpdateElectionForm
    model = Election
    permission_required = 'election_authority.can_edit_election'
    template_name_suffix = '_update'

    def get_success_url(self):
        return reverse('election-authority:election-update', kwargs={'slug': self.object.slug})


class ElectionCreateView(PermissionRequiredMixin, CreateView):
    form_class = CreateElectionForm
    model = Election
    permission_required = 'election_authority.can_create_election'
    template_name_suffix = '_create'

    def get_form_kwargs(self):
        kwargs = super(ElectionCreateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if 'preview_ballot' in self.request.POST:
            # Generate a preview of the election's ballot.
            pdf_file = generate_sample_ballot_pdf(form)
            pdf_data = force_text(base64.b64encode(pdf_file.getvalue()))
            return self.render_to_response(self.get_context_data(form=form, pdf_data=pdf_data))
        else:
            # Save the election and start the setup.
            with transaction.atomic():
                return super(ElectionCreateView, self).form_valid(form)


# API Views ###################################################################

class ElectionViewSet(SelectForUpdateMixin, GenericViewSet):
    lookup_field = 'slug'
    lookup_value_regex = r'[-\w]+'
    queryset = Election.objects.all()
    serializer_class = None
    authentication_classes = (HTTPSignatureAuthentication,)
    permission_classes = (DenyAll,)
    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer,)
    metadata_class = None


class BallotViewSet(SelectForUpdateMixin, GenericViewSet):
    lookup_field = 'serial_number'
    lookup_value_regex = r'[0-9]+'
    queryset = Ballot.objects.all()
    serializer_class = None
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
