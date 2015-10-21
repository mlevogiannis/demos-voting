# File: base32cf.py

import re
import math
from os import urandom
from random import getrandbits

# Reference: http://www.crockford.com/wrmg/base32.html


_chars = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

try:
    _translation = str.maketrans('OIL', '011')
    _str_translate = str.translate
except AttributeError:
    import string
    _translation = string.maketrans('OIL', '011')
    _str_translate = string.translate

_validation = re.compile('^[' + _chars + '-' + ']*$')


def encode(number, hyphens=-1):
	"""Encode an integer using base32cf. 'number' is the integer to encode.
	The encoded string is returned."""
	
	if number < 0:
		raise ValueError("argument is not a non-negative integer")
	
	encoded = '' if number else '0'
	
	while number:
		number, i = divmod(number, 32)
		encoded = _chars[i] + encoded
	
	if hyphens > 0:
		encoded = hyphen(encoded, hyphens)
	
	return encoded


def decode(encoded):
	"""Decode a base32cf encoded string. 'string' is the string to decode. 
	The resulting int is returned. ValueError is raised if there are
	non-alphabet characters present in the input."""
	
	number = 0
	
	encoded = normalize(encoded)
	encoded = hyphen(encoded, 0)
	
	for c in encoded:
		number = _chars.index(c) + number * 32
	
	return number


def random(length, hyphens=-1, crypto=True):
	"""Generate a random base32cf encoded string. 'length' is the length of
	final encoded string."""
	
	bits = length * 5
	bytes = int(math.ceil(bits / 8.0))
	shift_bits = (8 * bytes) - bits
	
	if crypto:
		number = int.from_bytes(urandom(bytes), 'big')
	else:
		number = getrandbits(bytes * 8)
	
	number = number >> shift_bits
	encoded = encode(number).zfill(length)
	
	if hyphens > 0:
		encoded = hyphen(encoded, hyphens)
	
	return encoded


def normalize(encoded, hyphens=-1):
	"""Normalize a base32c encoded string by replacing 'I' and 'L'
	with '1', replacing 'O' with '0' and convert all characters to uppercase.
	'string' is the string to normalize. ValuefError is raised if there are
	non-alphabet characters present in the input."""
	
	encoded = _str_translate(str(encoded).upper(), _translation)
	
	if not _validation.match(encoded):
		raise ValueError("Non-base32cf digit found")
	
	if hyphens > 0:
		encoded = hyphen(encoded, hyphens)
	
	return encoded


def hyphen(encoded, hyphens):
	"""Manage hyphens in a base32cf string. 'hyphens' controls how hyphens are
	treated, 0 means remove all, n > 0 means add a hyphen every n characters."""
	
	if hyphens >= 0:
		encoded = re.sub('-', '', encoded)
	
	if hyphens > 0:
		encoded = '-'.join(re.findall('.{,%s}' % hyphens, encoded)[:-1])
	
	return encoded

