# File: views.py

from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import itertools
import logging

from django import http
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import transaction
from django.middleware import csrf
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.encoding import force_text
from django.utils.six.moves import range, zip
from django.utils.six.moves.urllib.parse import quote, urljoin
from django.views.generic import View

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from celery.result import AsyncResult

from demos_voting.base.authentication import APIAuthentication
from demos_voting.base.utils import base32, pdf
from demos_voting.election_authority.forms import (
    ElectionForm, QuestionFormSet, OptionFormSet, PartyFormSet, CandidateFormSet, create_questions_and_options,
    create_trustees,
)
from demos_voting.election_authority.models import Election, Question, Option, Ballot, Trustee
from demos_voting.election_authority.serializers import ElectionSerializer, BallotSerializer
from demos_voting.election_authority.tasks import setup_task

logger = logging.getLogger(__name__)


class HomeView(View):

    template_name = 'election_authority/home.html'

    def get(self, request):
        return render(request, self.template_name, {})


class CreateView(View):

    template_name = 'election_authority/create.html'

    def get(self, request, *args, **kwargs):

        election_form = ElectionForm(prefix='election')
        question_formset = QuestionFormSet(prefix='questions')
        option_formsets = [(question_formset.empty_form, OptionFormSet(prefix='options__prefix__'))]

        context = {
            'election_form': election_form,
            'question_formset': question_formset,
            'option_formsets': option_formsets,
        }

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):

        # Peek at the election type.

        try:
            election_type = force_text(request.POST['election-type'])
            if election_type not in (Election.TYPE_ELECTION, Election.TYPE_REFERENDUM):
                raise ValueError
        except Exception:
            election_type = None

        # Peek at the number of questions.

        try:
            question_total_forms = int(request.POST['questions-TOTAL_FORMS'])
            if election_type == Election.TYPE_ELECTION:
                min_forms = QuestionFormSet.min_num
                max_forms = QuestionFormSet.max_num
            elif election_type == Election.TYPE_REFERENDUM:
                min_forms = PartyFormSet.min_num
                max_forms = PartyFormSet.max_num
            if question_total_forms < min_forms or question_total_forms > max_forms:
                raise ValueError
        except Exception:
            question_total_forms = None

        # Instatiate and validate the appropriate forms.

        is_valid = True

        if election_type == Election.TYPE_ELECTION:
            if question_total_forms:
                candidate_formsets = []
                for i in range(question_total_forms):
                    candidate_formset = CandidateFormSet(data=request.POST, prefix='options%s' % i)
                    candidate_formsets.append(candidate_formset)
                    is_valid =candidate_formset.is_valid() and is_valid
            else:
                candidate_formsets = None

            party_formset = PartyFormSet(
                data=request.POST,
                prefix='questions',
                form_kwargs={'candidate_formsets': candidate_formsets}
            )

            election_kwargs = {'party_formset': party_formset}
            is_valid = party_formset.is_valid() and is_valid

        elif election_type == Election.TYPE_REFERENDUM:
            if question_total_forms:
                option_formsets = []
                for i in range(question_total_forms):
                    option_formset = OptionFormSet(data=request.POST, prefix='options%s' % i)
                    option_formsets.append(option_formset)
                    is_valid = option_formset.is_valid() and is_valid
            else:
                option_formsets = None

            question_formset = QuestionFormSet(
                data=request.POST,
                prefix='questions',
                form_kwargs={'option_formsets': option_formsets}
            )

            election_kwargs = {'question_formset': question_formset}
            is_valid = question_formset.is_valid() and is_valid

        else:
            election_kwargs = {}

        election_form = ElectionForm(data=request.POST, prefix='election', **election_kwargs)
        is_valid = election_form.is_valid() and is_valid

        if is_valid:
            election = election_form.save(commit=False)

            trustees = create_trustees(election_form)
            questions, optionss = create_questions_and_options(election_form)

            election.generate_votecode_length()
            election.generate_security_code_length(optionss)

            if request.is_ajax():
                file = pdf.sample(election, questions, optionss)
                data = base64.b64encode(file.getvalue()).decode()
                return http.HttpResponse(data)

            else:
                with transaction.atomic():
                    election.state = Election.STATE_PENDING
                    election.save()

                    for trustee in trustees:
                        trustee.election_id = election.pk

                    Trustee.objects.bulk_create(trustees)

                    for question in questions:
                        question.election_id = election.pk

                    Question.objects.bulk_create(questions)

                    question_pks = Question.objects.filter(election=election).values_list('pk', flat=True)
                    for question_pk, options in zip(question_pks, optionss):
                        for option in options:
                            option.question_id = question_pk

                    Option.objects.bulk_create(itertools.chain.from_iterable(optionss))

                    setup_task.delay(election_id=election.id)

                return redirect('election_authority:status', election_id=election.id)

        else:
            if election_type == Election.TYPE_ELECTION:
                question_formset = party_formset
                option_formsets = candidate_formsets

            question_formset = question_formset or QuestionFormSet(prefix='questions')

            option_formsets = list(zip(question_formset, option_formsets or [])) + [
                (QuestionFormSet(prefix='questions').empty_form, OptionFormSet(prefix='options__prefix__'))
            ]

            question_formset_errors = sum(
                int(not(question_form.is_valid() and option_formset.is_valid()))
                for question_form, option_formset
                in option_formsets[:-1]
            )

            context = {
                'election_form': election_form,
                'question_formset': question_formset,
                'option_formsets': option_formsets,
                'question_formset_errors': question_formset_errors,
            }

            return render(request, self.template_name, context, status=422)


class StatusView(View):

    template_name = 'election_authority/status.html'

    def get(self, request, *args, **kwargs):

        election_id = kwargs.get('election_id')

        normalized = base32.normalize(election_id)
        if normalized != election_id:
            return redirect('election_authority:status', election_id=normalized)

        try:
            election = Election.objects.get(id=election_id)
        except Election.DoesNotExist:
            election = None

        if not election:
           return redirect(reverse('election_authority:home') + '?error=id')

        abb_url = urljoin(conf.URL['abb'], quote("results/%s/" % election_id))
        bds_url = urljoin(conf.URL['vbb'], quote("manage/%s/" % election_id))

        context = {
            'abb_url': abb_url,
            'bds_url': bds_url,
            'election': election,
            'State': {state.name: state.value for state in enums.State},
        }

        csrf.get_token(request)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):

        election_id = kwargs.get('election_id')

        if election_id is None:
            return http.HttpResponseNotAllowed(['GET'])

        response = {}

        try: # Return election creation progress

            election = Election.objects.get(id=election_id)

            celery = Task.objects.get(election=election)
            task = AsyncResult(str(celery.task_id))

            response['state'] = enums.State.WORKING.value
            response.update(task.result or {})

        except Task.DoesNotExist:

            # Return election state or invalid

            if election.state.value == enums.State.RUNNING.value:
                if timezone.now() < election.starts_at:
                    response['not_started'] = True
                elif timezone.now() > election.ends_at:
                    response['ended'] = True

            response['state'] = election.state.value

        except (ValidationError, Election.DoesNotExist):
            return http.HttpResponse(status=422)

        return http.JsonResponse(response)


class CenterView(View):

    template_name = 'election_authority/center.html'

    def get(self, request):
        # FIXME!
        return http.HttpResponse(status=404)


# API Views -------------------------------------------------------------------

class ElectionViewSet(GenericViewSet):

    lookup_field = 'id'
    lookup_value_regex = base32.regex + r'+'
    queryset = Election.objects.all()
    serializer_class = ElectionSerializer
    authentication_classes = (APIAuthentication,)
    permission_classes = (IsAuthenticated,)


class BallotViewSet(GenericViewSet):

    lookup_field = 'serial_number'
    lookup_value_regex = r'[0-9]+'
    queryset = Ballot.objects.all()
    serializer_class = BallotSerializer
    authentication_classes = (APIAuthentication,)
    permission_classes = (IsAuthenticated,)


class TestAPIView(APIView):

    authentication_classes = (APIAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(data=None)

