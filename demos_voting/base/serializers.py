# File: serializers.py

from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework.serializers import BaseSerializer, ListSerializer


class DynamicFieldsMixin(object):
    """
    A Serializer mixin that takes an additional `fields` argument that
    controls which fields should be included or not. Nested serializers
    are supported. Each level's fields must be marked either to be
    included (True) or excluded (False). The rest are assumed to be
    excluded or included, respectively. E.g.:

    fields = {
        'id': True,
        'state': True,
        'questions': {
            'name': False,
        }
    }
    """

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', None)
        super(DynamicFieldsMixin, self).__init__(*args, **kwargs)
        if fields is not None:
            self._update_fields(self, fields)

    @classmethod
    def _update_fields(cls, serializer, fields):
        if isinstance(serializer, ListSerializer):
            serializer = serializer.child

        serializer_fields = set(serializer.fields.keys())
        included_fields = set()
        excluded_fields = set()
        nested_fields = set()

        for field_name, value in fields.items():
            if field_name not in serializer_fields:
                raise ValueError("Field `%s` does not exist." % field_name)
            else:
                if value is True:
                    included_fields.add(field_name)
                elif value is False:
                    excluded_fields.add(field_name)
                elif isinstance(value, dict):
                    nested_fields.add(field_name)
                else:
                    raise ValueError("Value `%s` is not valid for field `%s`." % (value, field_name))

        if included_fields and excluded_fields:
            raise ValueError("Fields must be marked either to be included (True) or excluded (False).")

        for field_name in (excluded_fields or (serializer_fields - (included_fields | nested_fields))):
            serializer.fields.pop(field_name)

        for field_name in nested_fields:
            field = serializer.fields[field_name]
            if not isinstance(field, BaseSerializer):
                raise ValueError("Field `%s` is not a nested serializer." % field_name)
            cls._update_fields(field, fields[field_name])

