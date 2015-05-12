# File: forms.py

import hmac
import zlib
import requests

from base64 import b85encode, b85decode

from django import forms
from django.core.files.uploadedfile import UploadedFile

from demos_utils.settings import *

HMAC_LEN = 2 * HASH_DIGEST_LEN


class TextForm(forms.Form):
	
	text_data = forms.CharField(min_length=1, max_length=RECV_MAX)
	text_hmac = forms.CharField(min_length=HMAC_LEN, max_length=HMAC_LEN)
	
	def clean(self):
		
		data = self.cleaned_data.get('text_data')
		digest1 = self.cleaned_data.get('text_hmac')
		
		if data and digest1:
			
			try:
				data = data.encode()
				
				digest2 = hmac.new(key=PRE_SHARED_KEY, msg=data,
					digestmod=HASH_ALG_NAME).hexdigest()
				
				if not hmac.compare_digest(digest1, digest2):
					raise forms.ValidationError("HMAC mismatch", code='invalid')
				
				data = b85decode(data)
				data = zlib.decompress(data)
				data = data.decode()
			
			except Exception as e:
				raise forms.ValidationError(str(e), code='invalid') from None
			
			else:
				self.cleaned_data['text_data'] = data


class FileForm(forms.Form):
	
	file_data = forms.FileField(max_length=TEXT_LEN, allow_empty_file=False)
	file_hmac = forms.CharField(min_length=HMAC_LEN, max_length=HMAC_LEN)
	
	def clean(self):
		
		data = self.cleaned_data.get('file_data')
		digest1 = self.cleaned_data.get('file_hmac')
		
		if data and digest1:
			
			try:
				hmac_obj = hmac.new(key=PRE_SHARED_KEY, digestmod=HASH_ALG_NAME)
				
				for chunk in data.chunks():
					hmac_obj.update(chunk)
				
				digest2 = hmac_obj.hexdigest()
				
				if not hmac.compare_digest(digest1, digest2):
					raise forms.ValidationError("HMAC mismatch", code='invalid')
			
			except Exception as e:
				raise forms.ValidationError(str(e), code='invalid') from None
			
			else:
				self.cleaned_data['file_data'].seek(0)


def post(url, text_data=None, file_data=None):
	
	args = {}
	
	# Prepare text data
	
	if text_data is not None:
		
		data = args.setdefault('data', {})
		
		text_data = text_data.encode()
		text_data = zlib.compress(text_data)
		text_data = b85encode(text_data)
		
		text_hmac = hmac.new(key=PRE_SHARED_KEY, msg=text_data,
			digestmod=HASH_ALG_NAME).hexdigest()
		
		text_data = text_data.decode()
		
		data['text_data'] = text_data
		data['text_hmac'] = text_hmac
	
	# Prepare file data
	
	if file_data is not None:
		
		data = args.setdefault('data', {})
		files = args.setdefault('files', {})
		
		hmac_obj = hmac.new(key=PRE_SHARED_KEY, digestmod=HASH_ALG_NAME)
		uploaded_file = UploadedFile(file_data)
		
		for chunk in uploaded_file.chunks():
			hmac_obj.update(chunk)
		
		file_hmac = hmac_obj.hexdigest()
		
		files['file_data'] = file_data.getvalue()
		data['file_hmac'] = file_hmac
	
	# Upload post request
	
	request = requests.post(url, verify=True, **args)
	request.raise_for_status()

