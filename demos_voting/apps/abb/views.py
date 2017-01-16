# File: views.py

from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib
import hmac
import logging
import math

from base64 import b64decode

from django import http
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Prefetch, Sum
from django.middleware import csrf
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.six.moves import range, zip
from django.views.generic import View

from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import DjangoModelPermissionsOrAnonReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from sendfile import sendfile

from demos_voting.apps.abb.authentication import APIAuthentication
from demos_voting.apps.abb.models import Election, Ballot
from demos_voting.apps.abb.serializers import ElectionSerializer, BallotSerializer
from demos_voting.common.utils import base32

logger = logging.getLogger(__name__)


class HomeView(View):

    template_name = 'abb/home.html'

    def get(self, request):
        return render(request, self.template_name, {})


class AuditView(View):

    template_name = 'abb/audit.html'

    def get(self, request, *args, **kwargs):

        election_id = kwargs.get('election_id')

        normalized = base32.normalize(election_id)
        if normalized != election_id:
            return redirect('abb:audit', election_id=normalized)

        try:
            election = Election.objects.get(id=election_id)
        except Election.DoesNotExist:
            election = None
        else:
            questions = Question.objects.filter(election=election)

        if not election:
            return redirect(reverse('abb:home') + '?error=id')

        participants = Ballot.objects.filter(election=election,
            part__optionv__voted=True).distinct().count() if election else 0

        context = {
            'election': election,
            'questions': questions,
            'participants': str(participants),
        }

        csrf.get_token(request)
        return render(request, self.template_name, context)


class ResultsView(View):

    template_name = 'abb/results.html'

    def get(self, request, *args, **kwargs):

        election_id = kwargs.get('election_id')

        normalized = base32.normalize(election_id)
        if normalized != election_id:
            return redirect('abb:results', election_id=normalized)

        try:
            election = Election.objects.get(id=election_id)
        except Election.DoesNotExist:
            election = None
        else:
            questions = Question.objects.filter(election=election)

        if not election:
            return redirect(reverse('abb:home') + '?error=id')

        participants = Ballot.objects.filter(election=election,
            part__optionv__voted=True).distinct().count() if election else 0

        questions = questions.annotate(Sum('optionc__votes'))

        context = {
            'election': election,
            'questions': questions,
            'participants': str(participants),
            'State': { s.name: s.value for s in enums.State },
        }

        csrf.get_token(request)
        return render(request, self.template_name, context)


# API Views -------------------------------------------------------------------

class ApiVoteView(View):

    #@method_decorator(api.user_required('vbb'))
    def dispatch(self, *args, **kwargs):
        return super(ApiVoteView, self).dispatch( *args, **kwargs)

    def get(self, request):

        csrf.get_token(request)
        return http.HttpResponse()

    def post(self, request, *args, **kwargs):

        try:
            votedata = api.ApiSession.load_json_request(request.POST)

            hasher = hashers.PBKDF2Hasher()

            e_id = votedata['e_id']
            b_serial = votedata['b_serial']
            b_credential = b64decode(votedata['b_credential'].encode())
            p1_tag = votedata['p1_tag']
            p1_votecodes = votedata['p1_votecodes']
            p2_security_code = votedata['p2_security_code']

            election = Election.objects.get(id=e_id)
            ballot = Ballot.objects.get(election=election, serial=b_serial)

            # part1 is always the part that the client has used to vote,
            # part2 is the other part.

            order = ('' if p1_tag == 'A' else '-') + 'tag'
            part1, part2 = Part.objects.filter(ballot=ballot).order_by(order)

            question_qs = Question.objects.filter(election=election)

            # Verify election state

            now = timezone.now()

            if not(election.state == enums.State.RUNNING and \
                now >= election.starts_at and now < election.ends_at):
                raise Exception('Invalid election state')

            # Verify ballot's credential

            if not hasher.verify(b_credential, ballot.credential_hash):
                raise Exception('Invalid ballot credential')

            # Verify part2's security code

            _, salt, iterations = part2.security_code_hash2.split('$')
            hash, _, _= hasher.encode(p2_security_code,salt[::-1], iterations, True)

            if not hasher.verify(hash, part2.security_code_hash2):
                raise Exception('Invalid part security code')

            # Check if the ballot is already used

            part_qs = [part1, part2]
            if OptionV.objects.filter(part__in=part_qs, voted=True).exists():
                raise Exception('Ballot already used')

            # Common long votecode values

            if election.long_votecodes:

                credential_int = int_from_bytes(b_credential, 'big')

                key = base32.decode(p2_security_code)
                bytes = int(math.ceil(key.bit_length() / 8))
                key = int_to_bytes(key, bytes, 'big')

            # Verify vote's correctness and save it to the db in an atomic
            # transaction. If anything fails, rollback and return the error.

            with transaction.atomic():
                for question in question_qs.iterator():

                    optionv_qs = OptionV.objects.filter(part=part1, question=question)
                    optionv2_qs = OptionV.objects.filter(part=part2, question=question)

                    vc_name = 'votecode'
                    vc_list = p1_votecodes[str(question.index)]

                    if len(vc_list) < question.min_choices:
                        raise Exception('Not enough votecodes')

                    if len(vc_list) > question.max_choices:
                        raise Exception('Too many votecodes')

                    # Long votecode version: use hashes instead of votecodes

                    if election.long_votecodes:

                        l_votecodes = vc_list

                        vc_list = [hasher.encode(vc, part1.l_votecode_salt,
                            part1.l_votecode_iterations, True)[0] for vc in vc_list]

                        vc_name = 'l_' + vc_name + '_hash'

                    # Get options for the requested votecodes

                    vc_filter = {vc_name + '__in': vc_list}

                    optionv_not_qs = optionv_qs.exclude(**vc_filter)
                    optionv_qs = optionv_qs.filter(**vc_filter)

                    # If lengths do not match, at least one votecode was invalid

                    if optionv_qs.count() != len(vc_list):
                        raise Exception('Invalid votecode')

                    # Save both voted and unvoted options

                    if election.short_votecodes:

                        optionv_qs.update(voted=True)
                        optionv_not_qs.update(voted=False)
                        optionv2_qs.update(voted=False)

                    elif election.long_votecodes:

                        # Save the requested long votecodes

                        for optionv, l_votecode in zip(optionv_qs, l_votecodes):
                            optionv.voted = True
                            optionv.l_votecode = l_votecode
                            optionv.save(update_fields=['voted', 'l_votecode'])

                        optionv_not_qs.update(voted=False)

                        # Compute part2's long votecodes

                        for optionv2 in optionv2_qs:

                            msg = credential_int + (question.index * election.max_options_cnt) + optionv2.votecode
                            bytes = int(math.ceil(msg.bit_length() / 8))
                            msg = int_to_bytes(msg, bytes, 'big')

                            hmac_obj = hmac.new(key, msg, hashlib.sha256)
                            digest = int_from_bytes(hmac_obj.digest(), 'big')

                            l_votecode = base32.encode(digest)[-conf.VOTECODE_LEN:]

                            optionv2.voted = False
                            optionv2.l_votecode = l_votecode
                            optionv2.save(update_fields=['voted', 'l_votecode'])

                # Save part2's security code

                part2.security_code = p2_security_code
                part2.save(update_fields=['security_code'])

        except Exception:
            logger.exception('VoteView: API error')
            return http.HttpResponse(status=422)

        return http.HttpResponse()


class ElectionViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):

    lookup_field = 'id'
    lookup_value_regex = base32.regex + r'+'
    queryset = Election.objects.none()
    serializer_class = ElectionSerializer
    authentication_classes = (APIAuthentication,)
    permission_classes = (DjangoModelPermissionsOrAnonReadOnly,)

    def get_queryset(self):
        return Election.objects.prefetch_related('questions__options')


class BallotViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):

    lookup_field = 'serial_number'
    lookup_value_regex = r'[0-9]+'
    queryset = Ballot.objects.none()
    serializer_class = BallotSerializer
    authentication_classes = (APIAuthentication,)
    permission_classes = (DjangoModelPermissionsOrAnonReadOnly,)

    def get_queryset(self):
        queryset = Ballot.objects.filter(election__id=self.kwargs['election_id'])
        queryset = queryset.prefetch_related('parts__questions__options')
        queryset = queryset.prefetch_related(Prefetch('election', Election.objects.only('state', 'votecode_type')))
        return queryset


class TestAPIView(APIView):

    authentication_classes = (APIAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(data=None)


# Media Views -----------------------------------------------------------------

class CertificateView(View):
    def get(self, request, election_id):
        election = get_object_or_404(Election.objects.only('certificate'), id=election_id)
        if not election.certificate:
            raise http.Http404("Election does not have a certificate.")
        return sendfile(request, election.certificate.path)

