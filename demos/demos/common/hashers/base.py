# File: base.py

from __future__ import absolute_import, division, print_function, unicode_literals


class BaseHasher(object):
    """
    Abstract base class for hashers
    
    Subclasses need to override algorithm, params(), salt(), encode(),
    verify(), split(), join() and __init__() (optional).
    """
    
    algorithm = None
    
    def __init__(self, conf):
        """
        Initializes the hasher using settings from conf
        """
    
    def params(self):
        """
        Returns the hasher's default parameters in ASCII
        """
        raise NotImplementedError('subclasses of BaseHasher must provide a params() method')
    
    def salt(self):
        """
        Generates a cryptographically secure nonce salt in ASCII
        """
        raise NotImplementedError('subclasses of BaseHasher must provide a salt() method')
    
    def encode(self, value, salt=None, params=None):
        """
        Creates an encoded database value
        """
        raise NotImplementedError('subclasses of BaseHasher must provide an encode() method')
    
    def verify(self, value, encoded):
        """
        Checks if the given value is correct
        """
        raise NotImplementedError('subclasses of BaseHasher must provide a verify() method')
    
    def split(self, encoded):
        """
        Splits an encoded value into params, salt and hash
        """
        raise NotImplementedError('subclasses of BaseHasher must provide a split() method')
    
    def join(self, params, salt, hash):
        """
        Joins params, salt and hash to an encoded value
        """
        raise NotImplementedError('subclasses of BaseHasher must provide a join() method')

