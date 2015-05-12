# File: fields.py

import zlib
import json

from base64 import b85encode, b85decode

from django.db import models
from django.core.exceptions import ValidationError


class IntEnumField(models.SmallIntegerField):
	
	description = "IntEnumField"
	
	def __init__(self, *args, **kwargs):
		
		self.cls = kwargs.pop('cls')
		super().__init__(*args, **kwargs)
	
	def deconstruct(self):
		
		name, path, args, kwargs = super().deconstruct()
		kwargs['cls'] = self.cls
		return name, path, args, kwargs
	
	def get_prep_value(self, value):
		
		if value is None:
			return value
		
		return value.value
	
	def from_db_value(self, value, expression, connection, context):
		
		if value is None:
			return value
		
		return self.cls(value)
	
	def value_to_string(self, obj):
		
		value = self._get_val_from_obj(obj)
		value = self.get_prep_value(value)
		return str(value)
	
	def to_python(self, value):
		
		if value is None or isinstance(value, self.cls):
			return value
		
		try:
			value = int(value)
			value = self.cls(value)
		
		except Exception as e:
			raise ValidationError(str(e), code='invalid')
		
		return value


class JsonField(models.BinaryField):
	
	description = "JsonField"
	
	def __init__(self, *args, **kwargs):
		
		self.compressed = kwargs.pop('compressed', False)
		
		self.dump_kwargs = kwargs.pop('dump_kwargs', {})
		self.load_kwargs = kwargs.pop('load_kwargs', {})
		
		self.dump_kwargs['indent'] = None
		self.dump_kwargs['separators'] = (',', ':')
		
		super().__init__(*args, **kwargs)
	
	def deconstruct(self):
		
		name, path, args, kwargs = super().deconstruct()
		
		kwargs['compressed'] = self.compressed
		kwargs['dump_kwargs'] = self.dump_kwargs
		kwargs['load_kwargs'] = self.load_kwargs
		
		return name, path, args, kwargs
	
	def get_prep_value(self, value):
		
		if value is None:
			return value
		
		if not isinstance(value, dict):
			raise TypeError("Expected dict object")
		
		value = json.dumps(value, **self.dump_kwargs)
		value = value.encode()
		
		if self.compressed:
			value = zlib.compress(value)
		
		return value
	
	def from_db_value(self, value, expression, connection, context):
		
		if value is None:
			return value
		
		if self.compressed:
			value = zlib.decompress(value)
		
		value = value.decode()
		value = json.loads(value, **self.load_kwargs)
		
		return value
	
	def value_to_string(self, obj):
		
		value = self._get_val_from_obj(obj)
		value = self.get_prep_value(value)
		
		if self.compressed:
			value = b85encode(value)
		
		return value.decode()
	
	def to_python(self, value):
		
		if value is None or isinstance(value, dict):
			return value
		
		try:
			if self.compressed:
				value = value.encode()
				value = b85decode(value)
				value = zlib.decompress(value)
				value = value.decode()
			
			value = json.loads(value, **self.load_kwargs)
			
		except Exception as e:
			raise ValidationError(str(e), code='invalid')
		
		return value

