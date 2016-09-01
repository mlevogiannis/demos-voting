# File float.py

from __future__ import absolute_import, division, print_function, unicode_literals

from django import template

register = template.Library()


@register.filter
def floatadd(value, arg):
    try:
        return float(value) + float(arg)
    except Exception:
        return ''

@register.filter
def floatsub(value, arg):
    try:
        return float(value) - float(arg)
    except Exception:
        return ''

@register.filter
def floatmul(value, arg):
    try:
        return float(value) * float(arg)
    except Exception:
        return ''

@register.filter
def floatdiv(value, arg):
    try:
        return float(value) / float(arg)
    except Exception:
        return ''

