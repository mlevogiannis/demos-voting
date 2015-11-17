# File: views.py

from __future__ import division, unicode_literals

import json
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

from demos.common.utils import api, dbsetup
from demos.common.utils.config import registry

logger = logging.getLogger(__name__)
app_config = apps.get_app_config('bds')
config = registry.get_config('bds')


class HomeView(View):
    
    template_name = 'bds/home.html'
    
    def get(self, request):
        return render(request, self.template_name, {})


class ManageView(View):
    
    template_name = 'bds/manage.html'
    
    def get(self, request, election_id):
        f = http.FileResponse(open(config.TARSTORAGE_ROOT + '/' + election_id + '.tar', 'rb'), content_type='application/force-download')
        f['Content-Disposition'] = 'attachment; filename=%s' % election_id+'.tar'
        return f


class SetupView(View):
    
    @method_decorator(api.user_required('ea'))
    def dispatch(self, *args, **kwargs):
        return super(SetupView, self).dispatch(*args, **kwargs)
    
    def get(self, request):
        csrf.get_token(request)
        return http.HttpResponse()
    
    def post(self, request, *args, **kwargs):
        
        try:
            task = request.POST['task']
            election_obj = json.loads(request.POST['payload'])
            
            if task == 'election':
                dbsetup.election(election_obj, app_config)
                
            elif task == 'ballot':
                tarbuf = request.FILES['ballots.tar.gz']
        
                if hasattr(tarbuf, 'temporary_file_path'):
                    arg = {'name': tarbuf.temporary_file_path()}
                else:
                    arg = {'fileobj': BytesIO(tarbuf.read())}
        
                tar = tarfile.open(mode='r:*', **arg)
        
                for ballot_obj in election_obj['__list_Ballot__']:
            
                    pdfname = "%s.pdf" % ballot_obj['serial']
            
                    tarinfo = tar.getmember(pdfname)
                    pdfbuf = BytesIO(tar.extractfile(tarinfo).read())
            
                    ballot_obj['pdf'] = File(pdfbuf, name=pdfname)
                    
                dbsetup.ballot(election_obj, app_config)
                
            else:
                raise Exception('SetupView: Invalid POST task: %s' % task)
                
        except Exception:
            logger.exception('SetupView: API error')
            return http.HttpResponse(status=422)
        
        return http.HttpResponse()


class UpdateView(View):
    
    @method_decorator(api.user_required('ea'))
    def dispatch(self, *args, **kwargs):
        return super(UpdateView, self).dispatch(*args, **kwargs)
    
    def get(self, request):
        csrf.get_token(request)
        return http.HttpResponse()
    
    def post(self, request, *args, **kwargs):
        
        try:
            data = json.loads(request.POST['data'])
            model = app_config.get_model(data['model'])
            
            fields = data['fields']
            natural_key = data['natural_key']
            
            obj = model.objects.get_by_natural_key(**natural_key)
            
            for name, value in fields.items():
                setattr(obj, name, value)
                
            obj.save(update_fields=list(fields.keys()))
            
        except Exception:
            logger.exception('UpdateView: API error')
            return http.HttpResponse(status=422)
        
        return http.HttpResponse()

