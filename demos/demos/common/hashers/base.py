# File: base.py

from __future__ import absolute_import, division, unicode_literals

import random
import string

from django.utils.encoding import force_text
from django.utils.six.moves import range

random = random.SystemRandom()


class BaseHasher(object):
    """
    Abstract base class for hashers
    
    Subclasses need to override algorithm, encode() and verify().
    """
    
    algorithm = None
    separator = ':'
    
    _allowed_salt_chars = string.ascii_letters + string.digits
    
    def split(self, encoded):
        """
        Splits an encoded value into options, salt and hash
        """
        return tuple(encoded.rsplit(self.separator, 2))
    
    def join(self, options, salt, hash):
        """
        Joins options, salt and hash to an encoded value
        """
        return self.separator.join([force_text(options), salt, hash])
    
    def salt(self, length=22):
        """
        Generates a cryptographically secure nonce salt in ASCII
        
        The default length of 22 returns log_2((26+26+10)^22) =~ 130 bits.
        """
        return ''.join(random.choice(self._allowed_salt_chars) for i in range(length))
    
    def encode(self, value, salt=None, options=None):
        """
        Creates an encoded database value

        The result is formatted as "options:salt:hash", and must be fewer
        than 128 characters.
        """
        raise NotImplementedError('subclasses of BaseHasher must provide an encode() method')
    
    def verify(self, value, encoded):
        """
        Checks if the given value is correct
        """
        raise NotImplementedError('subclasses of BaseHasher must provide a verify() method')

