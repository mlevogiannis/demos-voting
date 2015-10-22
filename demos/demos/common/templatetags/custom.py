# File common.py

from django import template
from django.utils import timezone

register = template.Library()

@register.assignment_tag(name='now')
def now_(*args):
    return timezone.now()

@register.assignment_tag(name='tuple')
def tuple_(*args):
    return tuple(args)

@register.filter(name='div')
def div_(value, arg):
    try:
        return value / arg
    except Exception:
        return ''

