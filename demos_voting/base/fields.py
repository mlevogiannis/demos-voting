from __future__ import absolute_import, division, print_function, unicode_literals

import json

from django import forms
from django.core import exceptions
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import validate_email
from django.db import models
from django.utils.translation import ugettext_lazy as _, ungettext_lazy

from rest_framework import serializers


# Model fields ################################################################

class JSONField(models.TextField):
    description = "JSONField"

    default_dumps_kwargs = {
        'indent': None,
        'separators': (',', ':'),
        'sort_keys': True,
    }
    default_loads_kwargs = {}

    def __init__(self, *args, **kwargs):
        self.dumps_kwargs = kwargs.pop('dumps_kwargs', {})
        self.loads_kwargs = kwargs.pop('loads_kwargs', {})
        super(JSONField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(JSONField, self).deconstruct()
        kwargs['dumps_kwargs'] = self.dumps_kwargs
        kwargs['loads_kwargs'] = self.loads_kwargs
        return name, path, args, kwargs

    def _json_dumps(self, value):
        dumps_kwargs = self.default_dumps_kwargs.copy()
        dumps_kwargs.update(self.dumps_kwargs)
        try:
            return json.dumps(value, **dumps_kwargs)
        except Exception as e:
            raise exceptions.ValidationError(e, code='invalid')

    def _json_loads(self, value):
        loads_kwargs = self.default_loads_kwargs.copy()
        loads_kwargs.update(self.loads_kwargs)
        try:
            return json.loads(value, **loads_kwargs)
        except Exception as e:
            raise exceptions.ValidationError(e, code='invalid')

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        return self._json_loads(value)

    def to_python(self, value):
        if value is None or isinstance(value, (dict, list)):
            return value
        return self._json_loads(value)

    def get_prep_value(self, value):
        if value is None:
            return value
        return self._json_dumps(value)

    def value_to_string(self, obj):
        return self.get_prep_value(self.value_from_object(obj))


# Form fields #################################################################

class MultiEmailField(forms.CharField):
    def __init__(self, *args, **kwargs):
        self.min_num = kwargs.pop('min_num', None)
        self.max_num = kwargs.pop('max_num', None)
        self.case_insensitive = kwargs.pop('case_insensitive', False)
        super(MultiEmailField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        """
        Normalize data to a list of strings.
        """
        value = super(MultiEmailField, self).to_python(value)
        if not value:
            return []
        return [value.strip() for value in value.split(',')]

    def validate(self, value):
        """
        Check if value consists only of valid emails.
        """
        super(MultiEmailField, self).validate(value)
        if self.min_num is not None and len(value) < self.min_num:
            raise ValidationError(
                ungettext_lazy(
                    "Please submit %d or more email addresses.",
                    "Please submit %d or more email addresses.", self.min_num
                ) % self.min_num,
                code='too_few_values'
            )
        elif self.max_num is not None and len(value) > self.max_num:
            raise ValidationError(
                ungettext_lazy(
                    "Please submit %d or fewer email addresses.",
                    "Please submit %d or fewer email addresses.", self.max_num
                ) % self.max_num,
                code='too_many_values',
            )
        emails = set()
        for email in value:
            validate_email(email)
            if self.case_insensitive:
                email = email.lower()
            if email in emails:
                raise forms.ValidationError(_("All email addresses must be unique."), code='unique')
            emails.add(email)


# Serializer fields ###########################################################

class ContentFileField(serializers.FileField):
    """
    The `ContentFileField` inherits from `FileField` but unlike `FileField` it
    operates on text content rather than an actual file.
    """

    def to_internal_value(self, data):
        data = ContentFile(data, name=self.field_name)
        return super(ContentFileField, self).to_internal_value(data)
