# File: fields.py

import re

from django import forms
from django.core import validators


class MultiEmailField(forms.Field):
	
	def __init__(self, min_length=None, max_length=None, *args, **kwargs):
		
		self.min_length, self.max_length = min_length, max_length * 254
		super().__init__(*args, **kwargs)
		
		if min_length is not None:
			min_validator = validators.MinLengthValidator(int(min_length))
			self.validators.append(min_validator)
		
		if max_length is not None:
			max_validator = validators.MaxLengthValidator(int(max_length))
			self.validators.append(max_validator)
	
	def to_python(self, value):
		'''Normalize data to a list of strings.'''
		
		if not value:
			value_list = []
		else:
			value_list = re.split(r'[\s,]+', value)
			value_list = sorted(filter(None, set(value_list)))
		
		return value_list

	def validate(self, value):
		'''Check if value consists only of valid emails.'''
		
		super().validate(value)

		for email in value:
			validators.validate_email(email)

	def widget_attrs(self, widget):
		'''Set the HTML attribute maxlength'''
		
		attrs = super().widget_attrs(widget)
		
		if self.max_length is not None:
			attrs.update({'maxlength': str(self.max_length)})
		
		return attrs

