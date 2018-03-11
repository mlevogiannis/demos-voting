from __future__ import absolute_import, division, print_function, unicode_literals

import re

from six.moves import zip_longest

from demos_voting.base.utils.compat import int_from_bytes, int_to_bytes

# Reference: http://www.crockford.com/wrmg/base32.html

chars = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
regex = r'(?!-)(?:-?[0-9A-TV-Za-tv-z])'


# Encode ######################################################################

def encode(n, length=None, group_length=None):
    """Encode a string using Crockford's Base32."""
    if n < 0:
        raise ValueError("'%d' is not a non-negative integer." % n)
    elif n == 0:
        encoded = '0'
    else:
        encoded = ''
        while n > 0:
            encoded = chars[n & 31] + encoded
            n >>= 5
    if length is not None:
        encoded = encoded.zfill(length)
    if group_length is not None:
        encoded = hyphenate(encoded, group_length)
    return encoded


def encode_from_bytes(b, *args, **kwargs):
    n = int_from_bytes(b, 'big')
    return encode(n, *args, **kwargs)


# Decode ######################################################################

def decode(encoded):
    """Decode a Crockford's Base32 encoded string."""
    encoded = normalize(encoded)
    n = 0
    for c in encoded:
        n = chars.index(c) + (n << 5)
    return n


def decode_to_bytes(encoded, length=0, *args, **kwargs):
    n = decode(encoded, *args, **kwargs)
    return int_to_bytes(n, max([length, (n.bit_length() + 7) // 8]), 'big')


# Validate ####################################################################

_validation_regex = re.compile(r'^%s+$' % regex)


def validate(encoded):
    """Validate a Crockford's Base32 encoded string."""
    if not _validation_regex.match(encoded):
        raise ValueError("'%s' is not a valid Crockford's Base32 encoded string." % encoded)


# Normalize ###################################################################

try:
    _normalization_table = str.maketrans('OIL', '011', '-')
except AttributeError:
    _normalization_table = {ord(x): ord(y) if y else None for x, y in zip_longest('OIL-', '011')}


def normalize(encoded):
    """Normalize a Crockford's Base32 encoded string."""
    validate(encoded)
    return encoded.upper().translate(_normalization_table)


# Hyphenate ###################################################################

def hyphenate(encoded, group_length):
    """Hyphenate a Crockford's Base32 encoded string."""
    validate(encoded)
    if group_length < 0:
        raise ValueError("'%d' is not a non-negative integer." % group_length)
    else:
        encoded = encoded.replace('-', '')
        if group_length > 0:
            encoded = '-'.join(re.findall('.{,%s}' % group_length, encoded)[:-1])
    return encoded
