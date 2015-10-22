# File custom.py

from demos.common.templatetags.custom import *

@register.filter
def addfloat(value, arg):
    """Adds the arg to the value."""
    try:
        return float(value) + float(arg)
    except Exception:
        return ''
