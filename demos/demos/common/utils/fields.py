# File: fields.py

from __future__ import division, unicode_literals

import re

from base64 import b64encode, b64decode

from django import forms
from django.db import models
from django.core import validators
from django.utils import six
from django.utils.dateparse import parse_datetime
from django.core.exceptions import ValidationError

from demos.common.utils import base32cf


# Model fields -----------------------------------------------------------------

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
        
        if value is None or isinstance(value, six.integer_types):
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
        
        if value is None or isinstance(value, six.integer_types):
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
            if isinstance(value, six.string_types):
                value = b64decode(value.encode('ascii'))
            elif isinstance(value, self.cls):
                value = value.SerializeToString()
        except Exception as e:
            raise ValidationError(e, code='invalid')
        
        return value
    
    def value_to_string(self, obj):
        
        return b64encode(obj).decode('ascii')


# Form fields -----------------------------------------------------------------

class MultiEmailField(forms.Field):
    
    def __init__(self, min_length=None, max_length=None, *args, **kwargs):
        
        self.min_length, self.max_length = min_length, max_length * 254
        super(MultiEmailField, self).__init__(*args, **kwargs)
        
        if min_length is not None:
            min_validator = validators.MinLengthValidator(int(min_length))
            self.validators.append(min_validator)
        
        if max_length is not None:
            max_validator = validators.MaxLengthValidator(int(max_length))
            self.validators.append(max_validator)
    
    def to_python(self, value):
        """Normalize data to a list of strings."""
        
        if not value:
            value_list = []
        else:
            value_list = re.split(r'[\s;,]+', value)
            value_list = sorted(filter(None, set(value_list)))
        
        return value_list

    def validate(self, value):
        """Check if value consists only of valid emails."""
        
        super(MultiEmailField, self).validate(value)

        for email in value:
            validators.validate_email(email)

    def widget_attrs(self, widget):
        """Set the HTML attribute maxlength"""
        
        attrs = super(MultiEmailField, self).widget_attrs(widget)
        
        if self.max_length is not None:
            attrs.update({'maxlength': str(self.max_length)})
        
        return attrs


class DateTimeField(forms.DateTimeField):
    """DateTimeField that supports the ISO8601 format"""
    
    def to_python(self, value):
        
        if isinstance(value, six.string_types):
            try:
                parsed_value = parse_datetime(value)
            except ValueError:
                pass
            else:
                if parsed_value is not None:
                    value = parsed_value
        
        return super(DateTimeField, self).to_python(value)

