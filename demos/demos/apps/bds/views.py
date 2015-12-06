# File: views.py

from __future__ import absolute_import, division, unicode_literals

import logging
import tarfile

from io import BytesIO

from django import http
from django.db import transaction
from django.apps import apps
from django.shortcuts import render
from django.middleware import csrf
from django.core.files import File
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse

from demos.apps.bds.models import Election

from demos.common.utils import api

logger = logging.getLogger(__name__)

app_config = apps.get_app_config('bds')
conf = app_config.get_constants_and_settings()


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


# API Views --------------------------------------------------------------------

class ApiSetupView(api.ApiSetupView):
    
    def __init__(self, *args, **kwargs):
        kwargs['app_config'] = app_config
        super(ApiSetupView, self).__init__(*args, **kwargs)
    
    @method_decorator(api.user_required('ea'))
    def dispatch(self, *args, **kwargs):
        return super(ApiSetupView, self).dispatch(*args, **kwargs)
    
    def post(self, request, phase):
        
        try:
            election_obj = api.ApiSession.load_json_request(request.POST)
            
            if phase == 'p2':
                
                tarbuf = request.FILES['ballots.tar.gz']
                
                if hasattr(tarbuf, 'temporary_file_path'):
                    arg = {'name': tarbuf.temporary_file_path()}
                else:
                    arg = {'fileobj': tarbuf}
                
                tar = tarfile.open(mode='r:*', **arg)
                
                for ballot_obj in election_obj['__list_Ballot__']:
                    
                    pdfname = "%s.pdf" % ballot_obj['serial']
                    
                    tarinfo = tar.getmember(pdfname)
                    pdfbuf = tar.extractfile(tarinfo)
                    
                    ballot_obj['pdf'] = File(pdfbuf, name=pdfname)
                
        except Exception:
            logger.exception('SetupView: API error')
            return http.HttpResponse(status=422)
        
        return super(ApiSetupView, self).post(request, election_obj)


class ApiUpdateView(api.ApiUpdateView):
    
    def __init__(self, *args, **kwargs):
        kwargs['app_config'] = app_config
        super(ApiUpdateView, self).__init__(*args, **kwargs)
    
    @method_decorator(api.user_required('ea'))
    def dispatch(self, *args, **kwargs):
        return super(ApiUpdateView, self).dispatch(*args, **kwargs)

