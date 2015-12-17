# File: __init__.py

from __future__ import absolute_import, division, unicode_literals

from django.utils.lru_cache import lru_cache

from demos.common.conf import constants
from demos.common.hashers import base, pbkdf2


@lru_cache()
def get_hashers():
    def _yield_hasher(hasher):
        for hasher in hasher.__subclasses__():
            if getattr(hasher, 'algorithm', None):
                yield hasher
            for hasher in _yield_hasher(hasher):
                yield hasher
    return [hasher() for hasher in _yield_hasher(base.BaseHasher)]


@lru_cache()
def get_hashers_by_algorithm():
    return {hasher.algorithm: hasher for hasher in get_hashers()}


def get_hasher(algorithm='default'):
    if algorithm == 'default':
        algorithm = constants.HASHER_ALG
    return get_hashers_by_algorithm()[algorithm]

