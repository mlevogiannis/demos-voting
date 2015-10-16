# File: base32.py

import math
from os import urandom
from random import getrandbits


# Reference: http://www.crockford.com/wrmg/base32.html

_symbols = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'

_encode_dict = {i: ch for i, ch in enumerate(_symbols)}
_decode_dict = {ch: i for i, ch in enumerate(_symbols)}

_normalize_map = str.maketrans('OIL', '011', '-')


def normalize(string):
	"""Normalize a Crockford's Base32 encoded string by replacing 'I' and 'L'
	with '1', replacing 'O' with '0' and convert all characters to uppercase.
	'string' is the string to normalize. ValueError is raised if there are
	non-alphabet characters present in the input."""
	
	if not isinstance(string, str):
		raise TypeError("argument should be a string, not '%s'" % type(string))
	
	encoded = string.upper().translate(_normalize_map)
	
	if not set(encoded).issubset(set(_symbols)):
		raise ValueError("argument is not a valid base32cf value")
	
	return encoded


def encode(number):
	"""Encode an integer using Crockford's Base32. 'number' is the integer to
	encode. The encoded string is returned."""
	
	if number < 0:
		raise ValueError("argument is not a non-negative integer")
	
	encoded = '' if number else '0'
	
	while number:
		number, i = divmod(number, 32)
		encoded = _encode_dict[i] + encoded
	
	return encoded


def decode(string):
	"""Decode a Crockford's Base32 encoded string. 'string' is the string to
	decode. The resulting int is returned. ValueError is raised if there are
	non-alphabet characters present in the input."""
	
	number = 0
	encoded = normalize(string)
	
	for c in encoded:
		number = _decode_dict[c] + number * 32
	
	return number


def random(length, crypto=True):
	"""Generate a random Crockford's Base32 encoded string. 'length' is the
	length of randomly encoded string."""
	
	bits = length * 5
	bytes = math.ceil(bits / 8)
	shift_bits = (8 * bytes) - bits
	
	if crypto:
		number = int.from_bytes(urandom(bytes), 'big')
	else:
		number = getrandbits(bytes * 8)
	
	number = number >> shift_bits
	return encode(number).zfill(length)

