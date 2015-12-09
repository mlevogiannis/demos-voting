# File: base32cf.py

from __future__ import absolute_import, division, unicode_literals

import math
import os
import re

from random import getrandbits
from demos.common.utils.int import int_from_bytes

# Reference: http://www.crockford.com/wrmg/base32.html


symbols = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

re_valid_charset = '-0-9A-TV-Za-tv-z'
re_valid = re.compile('^[' + re_valid_charset + ']*$')

re_normalized_charset = '0-9A-TV-Z'
re_normalized = re.compile('^[' + re_normalized_charset + ']*$')


try:
    _translation_table = str.maketrans('OIL', '011')
except AttributeError:
    import string
    _translation_table = string.maketrans('OIL', '011')


def encode(number, hyphens=0):
    """Encode an integer to base32cf string. 'number' is the integer to encode.
    The encoded string is returned."""
    
    if number < 0:
        raise ValueError("argument is not a non-negative integer")
    
    encoded = '' if number else '0'
    
    while number:
        
        d = number >> 5
        m = number - (d << 5)
        
        encoded = symbols[m] + encoded
        number = d
    
    if hyphens > 0:
        encoded = hyphen(encoded, hyphens)
    
    return encoded


def decode(encoded):
    """Decode a base32cf encoded string. 'string' is the string to decode.
    The resulting integer is returned. ValueError is raised if there are
    non-alphabet characters present in the input."""
    
    number = 0
    
    encoded = normalize(encoded)
    encoded = hyphen(encoded, 0)
    
    for c in encoded:
        number = symbols.index(c) + (number << 5)
    
    return number


def normalize(encoded, hyphens=0):
    """Normalize a base32cf encoded string by replacing 'I' and 'L' with '1',
    'O' with '0' and converting all characters to uppercase. 'string' is the
    string to normalize. ValueError is raised if there are non-alphabet
    characters present in the input."""
    
    if not re_valid.match(encoded):
        raise ValueError("Non-base32cf digit found")
    
    encoded = encoded.upper().translate(_translation_table)
    
    if hyphens >= 0:
        encoded = hyphen(encoded, hyphens)
    
    return encoded


def hyphen(encoded, hyphens):
    """Manage hyphens in a base32cf string. 'hyphens' controls how hyphens are
    treated, 0 means remove all, n > 0 means add a hyphen every n characters."""
    
    if hyphens >= 0:
        encoded = encoded.replace('-', '')
    
    if hyphens > 0:
        encoded = '-'.join(re.findall('.{,%s}' % hyphens, encoded)[:-1])
    
    return encoded


def random(length, hyphens=0, urandom=True):
    """Generate a random base32cf encoded string. 'length' is the length of
    resulting encoded string."""
    
    bits = length * 5
    bytes = int(math.ceil(bits / 8))
    shift_bits = (8 * bytes) - bits
    
    if urandom:
        number = int_from_bytes(os.urandom(bytes), 'big')
    else:
        number = getrandbits(bytes * 8)
    
    number = number >> shift_bits
    encoded = encode(number).zfill(length)
    
    if hyphens > 0:
        encoded = hyphen(encoded, hyphens)
    
    return encoded

