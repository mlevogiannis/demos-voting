# File: views.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from django import http
from django.shortcuts import render
from django.views.generic import View

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from demos_voting.ballot_distributor.models import Election, Ballot
from demos_voting.ballot_distributor.serializers import ElectionSerializer, BallotSerializer
from demos_voting.base.authentication import APIAuthentication
from demos_voting.base.utils import base32

logger = logging.getLogger(__name__)


class HomeView(View):

    template_name = 'ballot_distributor/home.html'

    def get(self, request):
        return render(request, self.template_name, {})


class ManageView(View):

    template_name = 'ballot_distributor/manage.html'

    def get(self, request, election_id):
        f = http.FileResponse(open(conf.TARSTORAGE_ROOT + '/' + election_id + '.tar', 'rb'), content_type='application/force-download')
        f['Content-Disposition'] = 'attachment; filename=%s' % election_id+'.tar'
        return f


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

