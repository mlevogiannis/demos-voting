# File: views.py

from django.db import transaction
from django.core import serializers, urlresolvers
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from demos_abb.models import Election, Question, Option, Ballot, Side, OptData

from demos_utils.forms import TextForm
from demos_utils.settings import *


class UpdateOrCreateView(View):
	
	@method_decorator(csrf_exempt)
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)
	
	def post(self, request, *args, **kwargs):
		
		json_form = TextForm(request.POST)
		
		if json_form.is_valid():
			
			json_data = json_form.cleaned_data['text_data']
			
			try:
				with transaction.atomic():
					
					for obj in serializers.deserialize('json', json_data):
						obj.save()
				
				return HttpResponse()
				
			except:
				pass
		
		return HttpResponseBadRequest()

