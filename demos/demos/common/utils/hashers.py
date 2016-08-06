# File: hashers.py

from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import hashlib
import os
import re

from django.utils.crypto import constant_time_compare, pbkdf2
from django.utils.encoding import force_bytes


# Modular Crypt Format
# https://pythonhosted.org/passlib/modular_crypt_format.html

# Hash: A complete Modular Crypt Format hash string.
# Identifier: A short string uniquely identifying a particular scheme.
# Config: A string containing the identifier, rounds, salt, etc.
# Digest: The output of the hash function.


class BaseHasher(object):
    
    identifier = None
    
    @classmethod
    def hash(cls, secret, config=None):
        raise NotImplementedError
    
    @classmethod
    def verify(cls, secret, hash):
        raise NotImplementedError
    
    @classmethod
    def config(cls):
        raise NotImplementedError
    
    @classmethod
    def digest(cls, secret, config):
        raise NotImplementedError
    
    @classmethod
    def identify(cls, hash_or_config):
        raise NotImplementedError
    
    @classmethod
    def split(cls, hash):
        raise NotImplementedError
    
    @classmethod
    def join(cls, config, digest):
        raise NotImplementedError


class PBKDF2SHA512Hasher(BaseHasher):
    
    identifier = 'pbkdf2-sha512'
    algorithm = hashlib.sha512
    iterations = 100000
    salt_length = 16
    
    @classmethod
    def hash(cls, secret, config=None):
        config = config or cls.config()
        return cls.join(config, cls.digest(secret, config))
    
    @classmethod
    def verify(cls, secret, hash):
        config, digest = cls.split(hash)
        hash2 = cls.hash(secret, config)
        return constant_time_compare(hash, hash2)
    
    @classmethod
    def config(cls):
        salt = cls._b64encode(os.urandom(cls.salt_length))
        return '$%s$%d$%s' % (cls.identifier, cls.iterations, salt)
    
    @classmethod
    def digest(cls, secret, config):
        if not cls.identify(config):
            raise ValueError("hash scheme could not be identified")
        iterations, salt = config.rsplit('$', 2)[1:]
        secret = force_bytes(secret)
        salt = cls._b64decode(force_bytes(salt))
        iterations = int(iterations)
        return cls._b64encode(pbkdf2(secret, salt, iterations, digest=cls.algorithm))
    
    @classmethod
    def identify(cls, hash_or_config):
        return hash_or_config.startswith('$%s$' % cls.identifier)
    
    @classmethod
    def split(cls, hash):
        raise hash.rsplit('$', 1)
    
    @classmethod
    def join(cls, config, digest):
        return '%s$%s' % (config, digest)
    
    @staticmethod
    def _b64encode(s):
        return base64.b64encode(s, b'./').rstrip(b'=')
    
    @staticmethod
    def _b64decode(s):
        return base64.b64decode(s + b'=' * (-len(s) % 4), b'./')


# ----------------------------------------------------------------------------

_hashers = {
    PBKDF2SHA512Hasher.identifier: PBKDF2SHA512Hasher,
}

def identify_hasher(hash_or_config):
    for identifier, hasher in _hashers.items():
        if hasher.identify(hash_or_config):
            return identifier

def get_hasher(identifier):
    return _hashers[identifier]

