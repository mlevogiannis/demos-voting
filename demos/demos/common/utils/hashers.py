# File: hashers.py

from __future__ import absolute_import, division, unicode_literals

from collections import OrderedDict

from django.utils.crypto import constant_time_compare, pbkdf2
from django.contrib.auth.hashers import PBKDF2PasswordHasher, mask_hash

from demos.common.utils import base32cf, intc


class PBKDF2Hasher(PBKDF2PasswordHasher):
    """A subclass of PBKDF2PasswordHasher."""
    
    iterations = 1000
    algorithm = "_pbkdf2"
    
    def __init__(self, iterations=None):
        
        if iterations is not None:
            self.iterations = iterations
        
        super(PBKDF2Hasher, self).__init__()
    
    def encode(self, password, salt=None, iterations=None, split=False):
        
        if salt is None:
            salt = self.salt()
        
        if iterations is None:
            iterations = self.iterations
        
        hash = pbkdf2(password, salt, int(iterations), digest=self.digest)
        hash = base32cf.encode(intc.from_bytes(hash, 'big'))
        
        out = (hash, salt, iterations)
        return out if split else ("%s$%s$%d" % out)
    
    def verify(self, password, encoded, salt=None, iterations=None):
        
        hash, salt, iterations = self._split_encoded(encoded, salt, iterations)
        
        encoded_2 = self.encode(password, salt, int(iterations))
        return constant_time_compare(encoded, encoded_2)

    def safe_summary(self, encoded, salt=None, iterations=None):
        
        hash, salt, iterations = self._split_encoded(encoded, salt, iterations)
        
        return OrderedDict([
            ('algorithm', self.algorithm),
            ('iterations', iterations),
            ('salt', mask_hash(salt)),
            ('hash', mask_hash(hash)),
        ])

    def must_update(self, encoded, salt=None, iterations=None):
        
        _, _, iterations = self._split_encoded(encoded, salt, iterations)
        
        return int(iterations) != self.iterations
    
    @staticmethod
    def _split_encoded(encoded, salt=None, iterations=None):
        
        assert (salt is None and iterations is None) \
            or (salt is not None and iterations is not None)
        
        hash = encoded
        
        if salt is None and iterations is None:
            hash, salt, iterations = encoded.split('$')
        
        return hash, salt, iterations

