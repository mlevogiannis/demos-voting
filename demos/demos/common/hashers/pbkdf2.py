# File: pbkdf2.py

from __future__ import absolute_import, division, unicode_literals

import base64
import hashlib

from demos.common.hashers.base import BaseHasher
from django.utils.crypto import constant_time_compare, pbkdf2


class PBKDF2HMACHasher(BaseHasher):
    """
    Secure hashing using the PBKDF2 algorithm
    
    Configured to use PBKDF2 + HMAC. Subclasses need to override
    algorithm, digest and iterations.
    """
    
    def encode(self, value, salt=None, options=None):
        
        salt = salt or self.salt()
        iterations = int(options or self.iterations)
        
        assert value is not None
        assert self.separator not in salt
        
        hash = pbkdf2(value, salt, iterations, digest=self.digest)
        hash = base64.b64encode(hash).decode('ascii')
        
        return self.join(iterations, salt, hash)
    
    def verify(self, value, encoded):
        
        iterations, salt, hash  = self.split(encoded)
        encoded2 = self.encode(value, salt, iterations)
        
        return constant_time_compare(encoded, encoded2)


class PBKDF2HMACSHA256Hasher(PBKDF2HMACHasher):
    
    algorithm = 'pbkdf2-hmac-sha256'
    digest = hashlib.sha256
    iterations = 10000


class PBKDF2HMACSHA512Hasher(PBKDF2HMACHasher):
    
    algorithm = 'pbkdf2-hmac-sha512'
    digest = hashlib.sha512
    iterations = 10000

