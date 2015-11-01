# File: fields.py

from __future__ import division

from base64 import b64encode, b64decode

from django.db import models
from django.core.exceptions import ValidationError

from demos.common.utils import base32cf
from six import string_types


class IntEnumField(models.SmallIntegerField):
    
    description = "IntEnumField"
    
    def __init__(self, *args, **kwargs):
        
        self.cls = kwargs.pop('cls')
        super(IntEnumField, self).__init__(*args, **kwargs)
    
    def deconstruct(self):
        
        name, path, args, kwargs = super(IntEnumField, self).deconstruct()
        kwargs['cls'] = self.cls
        return name, path, args, kwargs
    
    def from_db_value(self, value, expression, connection, context):
        
        if value is None:
            return value
        
        try:
            value = self.cls(value)
        except Exception as e:
            raise ValidationError(e, code='invalid')
        
        return value
    
    def to_python(self, value):
        
        if value is None or isinstance(value, self.cls):
            return value
        
        try:
            value = self.cls(int(value))
        except Exception as e:
            raise ValidationError(e, code='invalid')
        
        return value
    
    def get_prep_value(self, value):
        
        if value is None or type(value) == int:
            return value
        
        return value.value
    
    def value_to_string(self, obj):
        
        value = self._get_val_from_obj(obj)
        return str(self.get_prep_value(value))


class Base32Field(models.PositiveIntegerField):
    
    description = "Base32Field"
    
    def from_db_value(self, value, expression, connection, context):
        
        if value is None:
            return value
        
        try:
            value = base32cf.encode(value)
        except Exception as e:
            raise ValidationError(e, code='invalid')
        
        return value
    
    def to_python(self, value):
        
        if value is None:
            return value
        
        return str(value)
    
    def get_prep_value(self, value):
        
        if value is None or isinstance(value, int):
            return value
        
        try:
            value = base32cf.decode(value)
        except Exception as e:
            raise ValidationError(e, code='invalid')
        
        return value
    
    def value_to_string(self, obj):
        
        value = self._get_val_from_obj(obj)
        
        try:
            value = base32cf.encode(value)
        except Exception as e:
            raise ValidationError(e, code='invalid')
        
        return value


class ProtoField(models.BinaryField):
    
    description = "ProtoField"
    
    def __init__(self, *args, **kwargs):
        
        self.cls = kwargs.pop('cls')
        super(ProtoField, self).__init__(*args, **kwargs)
    
    def deconstruct(self):
        
        name, path, args, kwargs = super(ProtoField, self).deconstruct()
        kwargs['cls'] = self.cls
        return name, path, args, kwargs
    
    def from_db_value(self, value, expression, connection, context):
        
        if value is None:
            return value
        
        pb = self.cls()
        
        try:
            pb.ParseFromString(value)
        except Exception as e:
            raise ValidationError(e, code='invalid')
        
        return pb
    
    def to_python(self, value):
        
        if value is None or isinstance(value, self.cls):
            return value
        
        pb = self.cls()
        
        try:
            value = b64decode(value.encode('ascii'))
            pb.ParseFromString(value)
        except Exception as e:
            raise ValidationError(e, code='invalid')
        
        return pb
    
    def get_prep_value(self, value):
        
        if value is None:
            return value
        
        try:
            if isinstance(value, string_types):
                value = b64decode(value.encode('ascii'))
            elif isinstance(value, self.cls):
                value = value.SerializeToString()
        except Exception as e:
            raise ValidationError(e, code='invalid')
        
        return value
    
    def value_to_string(self, obj):
        
        return b64encode(obj).decode('ascii')

