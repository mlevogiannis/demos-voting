# File: pbkdf2.py

from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import hashlib
import random

from django.utils.crypto import constant_time_compare, pbkdf2
from django.utils.encoding import force_text
from django.utils.six.moves import range

from demos.common.hashers.base import BaseHasher

random = random.SystemRandom()


class PBKDF2Hasher(BaseHasher):
    """
    Secure hashing using the PBKDF2-HMAC algorithm
    """
    
    algorithm = 'pbkdf2-hmac'
    iterations = 64000
    
    separator = ':'
    
    salt_length = 22
    salt_charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    
    def __init__(self, conf):
        self.digest = getattr(hashlib, conf.hash_algorithm)
    
    def params(self):
        return force_text(self.iterations)
    
    def salt(self): # log_2((26+26+10)^22) =~ 130 bits
        return ''.join(random.choice(self.salt_charset) for i in range(self.salt_length))
    
    def encode(self, value, salt=None, params=None):
        
        salt = salt or self.salt()
        params = params or self.params()
        
        iterations = int(params)
        
        assert value is not None
        assert self.separator not in salt
        
        hash = pbkdf2(value, salt, iterations, digest=self.digest)
        hash = base64.b64encode(hash).decode('ascii')
        
        return self.join(params, salt, hash)
    
    def verify(self, value, encoded):
        
        iterations, salt, hash  = self.split(encoded)
        encoded2 = self.encode(value, salt, iterations)
        
        return constant_time_compare(encoded, encoded2)
    
    def split(self, encoded):
        return tuple(encoded.rsplit(self.separator, 2))
    
    def join(self, params, salt, hash):
        return self.separator.join([params, salt, hash])

