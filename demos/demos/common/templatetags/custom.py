# File common.py

from django import template
from django.utils import timezone

register = template.Library()

@register.assignment_tag(name='tuple')
def tuple_(*args):
    return tuple(args)

