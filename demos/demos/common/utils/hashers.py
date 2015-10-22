# File: hashers.py

from base64 import b64encode
from django.utils.crypto import constant_time_compare, pbkdf2
from django.contrib.auth.hashers import PBKDF2PasswordHasher


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
        hash = b64encode(hash).decode('ascii').strip()
        
        out = (hash, salt, iterations)
        return out if split else ("%s$%s$%d" % out)
    
    def verify(self, password, encoded, salt=None, iterations=None):
        
        assert (salt is None and iterations is None) \
            or (salt is not None and iterations is not None)
        
        if salt is None and iterations is None:
            hash, salt, iterations = encoded.split('$')
        else:
            hash = encoded
        
        encoded_2 = self.encode(password, salt, int(iterations))
        return constant_time_compare(encoded, encoded_2)
    
    def verify_list(self, password, encoded_list):
        """Checks if the given password is correct, by searching in a list of
        encoded hashes. Returns the matching hash's index or -1"""
        
        lru_cache = (None, None)
        
        for index, encoded in enumerate(encoded_list):
            
            iterations_c, salt_c = lru_cache
            _, salt, iterations  = encoded.split('$', 3)
            
            if iterations != iterations_c or salt != salt_c:
                
                lru_cache = (iterations, salt)
                encoded_2 = self.encode(password, salt, int(iterations))
            
            if constant_time_compare(encoded, encoded_2):
                return index
        
        return -1

