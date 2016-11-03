# File: fields.py

from __future__ import absolute_import, division, print_function, unicode_literals

import json

from django.core import exceptions
from django.db import models


class JSONField(models.TextField):

    description = "JSONField"

    indent = None
    separators = (',', ':')

    def __init__(self, *args, **kwargs):

        self.encoder = kwargs.pop('encoder', None)
        self.decoder = kwargs.pop('decoder', None)

        super(JSONField, self).__init__(*args, **kwargs)

    def deconstruct(self):

        name, path, args, kwargs = super(JSONField, self).deconstruct()

        kwargs['encoder'] = self.encoder
        kwargs['decoder'] = self.decoder

        return name, path, args, kwargs

    def _json_dumps(self, value):
        try:
            return json.dumps(value, cls=self.encoder, indent=self.indent, separators=self.separators)
        except Exception as e:
            raise exceptions.ValidationError(e, code='invalid')

    def _json_loads(self, value):
        try:
            return json.loads(value, cls=self.decoder)
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

        if not isinstance(value, (dict, list)):
            raise TypeError("expected dict or list")

        return self._json_dumps(value)

    def value_to_string(self, obj):
        return self.get_prep_value(self._get_val_from_obj(obj))

