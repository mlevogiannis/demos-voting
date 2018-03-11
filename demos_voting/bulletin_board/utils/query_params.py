from __future__ import absolute_import, division, print_function, unicode_literals

import re
from collections import OrderedDict

from django.utils.translation import ugettext_lazy as _

from rest_framework.exceptions import ParseError
from rest_framework.serializers import BaseSerializer, ListSerializer

DELIMITER = ','
SUB_SELECTION_OPENING = '('
SUB_SELECTION_CLOSING = ')'

TOKENIZER_REGEX = re.compile(r'^(%s|%s|%s|\w*)(.*)$' % (
    re.escape(DELIMITER),
    re.escape(SUB_SELECTION_OPENING),
    re.escape(SUB_SELECTION_CLOSING),
))

TOKEN_NONE, TOKEN_DELIMITER, TOKEN_FIELD, TOKEN_SERIALIZER = range(4)

ERROR_MESSAGES = {
    'syntax_error': _("Syntax error at character %(position)d."),
    'duplicate_field': _("Field `%(field_name)s` at character %(position)d was specified more than once."),
    'invalid_field': _("Field `%(field_name)s` at character %(position)d does not exist."),
    'invalid_nested_serializer': _("Field `%(field_name)s` at character %(position)d does not support sub-selection."),
}


def parse_fields_qs(fields_qs, serializer_class, exclude=False):
    """
    Parser for the `fields` query string parameter.
    e.g.: ?fields=slug,name,questions(index,name,options(index,name))
    """

    def _parse(fields_qs, serializer, position=0):
        fields = OrderedDict()
        last_token_type = TOKEN_NONE
        is_root_serializer = (position == 0)

        if isinstance(serializer, ListSerializer):
            serializer = serializer.child

        while fields_qs:
            token, fields_qs = TOKENIZER_REGEX.match(fields_qs).groups()
            if not token:
                raise ParseError(ERROR_MESSAGES['syntax_error'] % {'position': position})
            elif token == DELIMITER:
                if last_token_type not in (TOKEN_FIELD, TOKEN_SERIALIZER):
                    raise ParseError(ERROR_MESSAGES['syntax_error'] % {'position': position})
                else:
                    last_token_type = TOKEN_DELIMITER
            elif token == SUB_SELECTION_OPENING:
                if last_token_type not in (TOKEN_FIELD,):
                    raise ParseError(ERROR_MESSAGES['syntax_error'] % {'position': position})
                else:
                    nested_serializer_name = fields.popitem()[0]
                    nested_serializer = serializer.fields[nested_serializer_name]
                    if not isinstance(nested_serializer, BaseSerializer):
                        position -= len(nested_serializer_name)
                        raise ParseError(ERROR_MESSAGES['invalid_nested_serializer'] % {
                            'position': position,
                            'field_name': nested_serializer_name,
                        })
                    fields[nested_serializer_name], fields_qs, position = _parse(
                        fields_qs, nested_serializer, position + 1
                    )
                    last_token_type = TOKEN_SERIALIZER
            elif token == SUB_SELECTION_CLOSING:
                if is_root_serializer or last_token_type not in (TOKEN_FIELD, TOKEN_SERIALIZER):
                    raise ParseError(ERROR_MESSAGES['syntax_error'] % {'position': position})
                else:
                    last_token_type = TOKEN_SERIALIZER
                    break
            else:
                if last_token_type not in (TOKEN_NONE, TOKEN_DELIMITER):
                    raise ParseError(ERROR_MESSAGES['syntax_error'] % {'position': position})
                elif token not in serializer.fields or serializer.fields[token].write_only:
                    raise ParseError(ERROR_MESSAGES['invalid_field'] % {'position': position, 'field_name': token})
                elif token in fields:
                    raise ParseError(ERROR_MESSAGES['duplicate_field'] % {'position': position, 'field_name': token})
                else:
                    fields[token] = not exclude
                    last_token_type = TOKEN_FIELD
            position += len(token)

        if last_token_type not in (TOKEN_FIELD, TOKEN_SERIALIZER):
            raise ParseError(ERROR_MESSAGES['syntax_error'] % {'position': position})

        return fields, fields_qs, position

    return _parse(fields_qs, serializer_class())[0]
