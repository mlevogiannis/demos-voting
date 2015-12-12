# File: base32cf.py

from __future__ import absolute_import, division, unicode_literals

import math
import os
import random as _random
import re

from demos.common.utils.int import int_from_bytes
from django.utils.six.moves import zip_longest

# Reference: http://www.crockford.com/wrmg/base32.html


symbols = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

re_valid_charset = '-0-9A-TV-Za-tv-z'
re_valid = re.compile('^[' + re_valid_charset + ']*$')

re_normalized_charset = '0-9A-HJKMNP-TV-Z'
re_normalized = re.compile('^[' + re_normalized_charset + ']*$')


def encode(number, length=0, hyphens=0):
    """Encode an integer to base32cf string. 'number' is the integer to
    encode, if 'length' > 0 the resulting encoded string is padded on the
    left with zero digits until the given length is reached, if 'hyphens' > 0
    a hyphen is added every n characters. The encoded string is returned."""
    
    if number < 0:
        raise ValueError("Non-negative integer: %s" % number)
    
    encoded = ''
    
    while number:
        
        d = number >> 5
        m = number - (d << 5)
        
        encoded = symbols[m] + encoded
        number = d
    
    if length > 0:
        encoded = encoded.zfill(length)
    
    if hyphens > 0:
        encoded = hyphen(encoded, hyphens)
    
    return encoded or '0'


def decode(encoded):
    """Decode a base32cf encoded string. 'encoded' is the string to decode.
    The resulting integer is returned. ValueError is raised if 'encoded'
    contains non-alphabet symbols."""
    
    encoded = normalize(encoded)
    
    number = 0
    for c in encoded:
        number = symbols.index(c) + (number << 5)
    
    return number


def normalize(encoded):
    """Normalize a base32cf encoded string by removing all hyphens, converting
    all characters to upper-case, replacing 'I' and 'L' with '1', 'O' with '0'
    and removing any leading '0'. 'encoded' is the string to normalize.
    ValueError is raised if 'encoded' contains non-alphabet symbols."""
    
    if not re_valid.match(encoded):
        raise ValueError("Non-base32cf symbol: %s", encoded)
    
    try:
        table = str.maketrans('OIL', '011', '-')
    except AttributeError:
        table = {ord(x): ord(y) if y else None for x, y in zip_longest('OIL-', '011')}
    
    return encoded.upper().translate(table).lstrip('0')


def hyphen(encoded, hyphens):
    """Manage hyphens in a base32cf string. 'hyphens' controls how hyphens are
    treated, 0 removes all hyphens, n > 0 adds a hyphen every n characters.
    ValueError is raised if 'encoded' contains non-alphabet symbols."""
    
    if not re_valid.match(encoded):
        raise ValueError("Non-base32cf symbol: %s", encoded)
    
    if hyphens >= 0:
        encoded = encoded.replace('-', '')
    
    if hyphens > 0:
        encoded = '-'.join(re.findall('.{,%s}' % hyphens, encoded)[:-1])
    
    return encoded


def random(length, hyphens=0, urandom=False):
    """Generate a random base32cf encoded string. 'length' is the length of
    resulting encoded string, if 'hyphens' > 0 an hyphen is added every n
    characters, 'urandom' selects whether os.urandom or a pseudo-random number
    generator is used."""
    
    bits = length * 5
    
    if urandom:
        bytes = int(math.ceil(bits / 8))
        number = int_from_bytes(os.urandom(bytes), 'big') >> ((bytes * 8) - bits)
    else:
        number = _random.getrandbits(bits)
    
    return encode(number, length, hyphens)

