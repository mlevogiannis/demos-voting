# File: views.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging

from django import http
from django.shortcuts import render
from django.views.generic import View

logger = logging.getLogger(__name__)


class HomeView(View):

    template_name = 'bds/home.html'

    def get(self, request):
        return render(request, self.template_name, {})


class ManageView(View):

    template_name = 'bds/manage.html'

    def get(self, request, election_id):
        f = http.FileResponse(open(conf.TARSTORAGE_ROOT + '/' + election_id + '.tar', 'rb'), content_type='application/force-download')
        f['Content-Disposition'] = 'attachment; filename=%s' % election_id+'.tar'
        return f


# API Views -------------------------------------------------------------------
