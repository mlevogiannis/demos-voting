# File: views.py

import tarfile
from io import BytesIO

from django.db import transaction
from django.core import serializers, urlresolvers
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.core.files import File
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.files.uploadedfile import TemporaryUploadedFile

from demos_bds.models import Election, Ballot, Side, Trustee

from demos_utils.forms import TextForm, FileForm
from demos_utils.settings import *


class UpdateOrCreateView(View):
	
	@method_decorator(csrf_exempt)
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)
	
	def post(self, request, *args, **kwargs):
		
		json_form = TextForm(request.POST)
		pdf_form = FileForm(request.POST, request.FILES)
		
		if pdf_form.is_valid():
			
			pdf_data = pdf_form.cleaned_data['file_data']
			
			try:
				if isinstance(pdf_data, TemporaryUploadedFile):
					arg = {'name': pdf_data.temporary_file_path()}
				else: # if isinstance(pdf_data, InMemoryUploadedFile):
					arg = {'fileobj': BytesIO(pdf_data.read())}
				
				tar = tarfile.open(mode='r:*', **arg)
			
			except:
				raise
		
		if json_form.is_valid():
			
			json_data = json_form.cleaned_data['text_data']
			
			try:
				with transaction.atomic():
					
					for obj in serializers.deserialize('json', json_data):
						
						if isinstance(obj.object, Ballot):
							tarinfo = tar.getmember(obj.object.pdf.name)
							pdfbuf = BytesIO(tar.extractfile(tarinfo).read())
							obj.object.pdf.save(tarinfo.name, File(pdfbuf))
						
						obj.save()
				
				return HttpResponse()
			
			except:
				raise
		
		return HttpResponseBadRequest()

