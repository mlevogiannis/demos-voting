# File: fields.py

from __future__ import absolute_import, division, print_function, unicode_literals

import re

from django import forms
from django.core import validators
from django.utils.dateparse import parse_datetime
from django.utils.encoding import force_str
from django.utils.translation import ugettext as _
from django.utils.translation import ungettext


class ISO8601DateTimeField(forms.DateTimeField):

    def strptime(self, value, format):
        return parse_datetime(force_str(value))


class MultiEmailField(forms.CharField):

    def __init__(self, min_num, max_num, *args, **kwargs):
        self.min_num = min_num
        self.max_num = max_num
        super(MultiEmailField, self).__init__(*args, **kwargs)

    def prepare_value(self, value):
        return super(MultiEmailField, self).prepare_value(value)

    def to_python(self, value):
        value = super(MultiEmailField, self).to_python(value)
        value = value.strip()
        if not value:
            return []
        # FIXME: https://tools.ietf.org/html/rfc3696
        return re.split(r'[\s,]+', value.strip())

    def validate(self, value):
        super(MultiEmailField, self).validate(value)

        if len(value) < self.min_num:
            raise ValidationError(ungettext(
                "Please submit %d or more email addresses.",
                "Please submit %d or more email addresses.", self.min_num) % self.min_num,
                code='too_few_values'
            )

        if len(value) > self.max_num:
            raise ValidationError(ungettext(
                "Please submit %d or fewer email addresses.",
                "Please submit %d or fewer email addresses.", self.max_num) % self.max_num,
                code='too_many_values',
            )

        emails = set()
        for email in value:
            validators.EmailValidator(message=_("One or more email addresses are not valid."))(email)
            if email in emails:
                raise forms.ValidationError(self.error_messages['unique'], code='unique')
            emails.add(email)
