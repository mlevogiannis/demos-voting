from __future__ import absolute_import, division, print_function, unicode_literals

import itertools

from django import template
from django.utils import timezone
from django.template.defaultfilters import date

from six.moves import range, zip

register = template.Library()


@register.filter
def verbose_name(instance, field_name=None):
    obj = instance._meta
    if field_name is not None:
        obj = obj.get_field(field_name)
    return obj.verbose_name


@register.filter
def verbose_name_plural(instance):
    return instance._meta.verbose_name_plural


@register.filter
def mult(a, b):
    return a * b


@register.filter
def floor_div(a, b):
    return a // b


@register.filter(name='range')
def range_(stop):
    return range(stop)


@register.filter(name='zip')
def zip_(a, b):
    return zip(a, b)


@register.simple_tag(name='min')
def min_(*args):
    return min(*args)


@register.simple_tag(name='max')
def max_(*args):
    return max(*args)


@register.filter
def list_append(iterable, element):
    return itertools.chain(iterable, [element])


@register.filter
def list_get(iterable, index):
    return list(iterable)[index]


@register.filter
def chunkify(iterable, n):
    return zip(*([iter(iterable)] * n))


@register.simple_tag
def get_current_utc_offset():
    datetime_now = timezone.now()
    current_timezone = timezone.get_current_timezone()
    utc_offset = datetime_now.astimezone(current_timezone).strftime('%z')
    return utc_offset[:3] + ':' + utc_offset[3:]


@register.filter(expects_localtime=True, is_safe=False)
def date_strftime(value, arg):
    arg = arg.replace('%Y', 'Y')
    arg = arg.replace('%y', 'y')
    arg = arg.replace('%m', 'm')
    arg = arg.replace('%d', 'd')
    arg = arg.replace('%H', 'G')
    arg = arg.replace('%M', 'i')
    arg = arg.replace('%S', 's')
    return date(value, arg)
