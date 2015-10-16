# File custom.py

import math
from demos.common.templatetags.custom import *

@register.filter
def floordiv(value, arg):
	try:
		return int(value) // int(arg)
	except (ValueError, TypeError):
		try:
			return value // arg
		except Exception:
			return ''

@register.filter
def chunks(lst, n):
	
	try:
		lst = list(lst)
		n = int(n)
	except (ValueError, TypeError):
		return ''
	
	l = len(lst)
	i = 0
	r = []
	
	for _ in range(n):
		d = math.ceil(l / n)
		c = lst[i: i+d]
		r.append(c)
		n -= 1
		l -= len(c)
		i += d
	
	return r

