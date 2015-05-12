# File: base32cf.py

# Reference: http://www.crockford.com/wrmg/base32.html


_symbols = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'

_encode_dict = {i: ch for i, ch in enumerate(_symbols)}
_decode_dict = {ch: i for i, ch in enumerate(_symbols)}

_normalize_upper = str.maketrans('OIL', '011', '-')


def b32cf_encode(number):
	"""Encode an integer using Crockford's Base32.
	
	number is the integer to encode. The encoded string is returned.
	"""
	
	if number < 0:
		raise ValueError('%s is not a non-negative integer' % number)
	
	encoded = '' if number else '0'
	
	while number:
		number, i = divmod(number, 32)
		encoded = _encode_dict[i] + encoded
	
	return encoded


def b32cf_decode(encoded):
	"""Decode a Crockford's Base32 encoded string.
	
	encoded is the string to decode. The decoded integer is returned.
	ValueError is raised if there are non-alphabet characters present in the
	input.
	"""
	
	number = 0
	encoded = encoded.upper().translate(_normalize_upper)
	
	if not set(encoded).issubset(set(_symbols)):
		raise ValueError('Non-base32cf digit found')
	
	for c in encoded:
		number = _decode_dict[c] + number * 32
	
	return number

