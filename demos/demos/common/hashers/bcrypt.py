# File: bcrypt.py

from __future__ import absolute_import, division, print_function, unicode_literals

from demos.common.hashers.base import BaseHasher


class BCryptHasher(BaseHasher):
    """
    Secure hashing using the bcrypt algorithm
    """

