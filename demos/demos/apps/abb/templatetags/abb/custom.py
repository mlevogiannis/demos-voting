# File custom.py

from demos.common.templatetags.custom import *


@register.filter(name='floatdiv')
def floatdiv_(value, arg):
    try:
        return float(value) / float(arg)
    except Exception:
        return ''


@register.filter(name='floatmul')
def floatmul_(value, arg):
    return float(value) * float(arg)
