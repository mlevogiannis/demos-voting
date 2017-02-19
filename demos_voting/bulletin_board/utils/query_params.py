# File: query_params.py

from __future__ import absolute_import, division, print_function, unicode_literals

import re
from collections import OrderedDict

from rest_framework.exceptions import ParseError
from rest_framework.serializers import BaseSerializer, ListSerializer


class FieldsParser(object):
    """
    Parser for `fields` query string parameter.
    e.g.: ?fields=id,name,questions(index,name,options(index,name))
    """

    tokenizer_regex = re.compile(r'^(,|\(|\)|\w*)(.*)$')
    token_none, token_delimiter, token_field, token_serializer = range(4)

    error_messages = {
        'syntax_error': "Error at character %d: Syntax error.",
        'duplicate_field': "Error at character %d: Field \"%s\" was specified more than once.",
        'invalid_field': "Error at character %d: Field \"%s\" does not exist.",
        'invalid_nested_serializer': "Error at character %d: Field \"%s\" does not support sub-selection.",
    }

    def __init__(self, serializer_class, exclude=False):
        self.serializer = serializer_class()
        self.exclude = exclude

    def parse(self, fields_str):
        if fields_str:
            return self._parse(fields_str, self.serializer)[0]

    def _parse(self, fields_str, serializer, position=0):
        if isinstance(serializer, ListSerializer):
            serializer = serializer.child

        fields = OrderedDict()

        token = None
        last_token_type = self.token_none
        is_root_serializer = (position == 0)

        while fields_str:
            token, fields_str = self.tokenizer_regex.match(fields_str).groups()

            if not token:
                raise ParseError(self.error_messages['syntax_error'] % position)
            elif token == ',':
                if last_token_type not in (self.token_field, self.token_serializer):
                    raise ParseError(self.error_messages['syntax_error'] % position)
                else:
                    last_token_type = self.token_delimiter
            elif token == '(':
                if last_token_type not in (self.token_field,):
                    raise ParseError(self.error_messages['syntax_error'] % position)
                else:
                    nested_serializer_name = fields.popitem()[0]
                    nested_serializer = serializer.fields[nested_serializer_name]
                    if not isinstance(nested_serializer, BaseSerializer):
                        position -= len(nested_serializer_name)
                        raise ParseError(
                            self.error_messages['invalid_nested_serializer'] % (position, nested_serializer_name)
                        )
                    fields[nested_serializer_name], fields_str, position = self._parse(
                        fields_str, nested_serializer, position + 1
                    )
                    last_token_type = self.token_serializer
            elif token == ')':
                if is_root_serializer or last_token_type not in (self.token_field, self.token_serializer):
                    raise ParseError(self.error_messages['syntax_error'] % position)
                else:
                    last_token_type = self.token_serializer
                    break
            else:
                if last_token_type not in (self.token_none, self.token_delimiter):
                    raise ParseError(self.error_messages['syntax_error'] % position)
                elif token not in serializer.fields or serializer.fields[token].write_only:
                    raise ParseError(self.error_messages['invalid_field'] % (position, token))
                elif token in fields:
                    raise ParseError(self.error_messages['duplicate_field'] % (position, token))
                else:
                    fields[token] = not self.exclude
                    last_token_type = self.token_field

            position += len(token)

        if last_token_type not in (self.token_field, self.token_serializer):
            raise ParseError(self.error_messages['syntax_error'] % position)

        return fields, fields_str, position

