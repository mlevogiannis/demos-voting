# File: __init__.py

from __future__ import absolute_import, division, print_function, unicode_literals

from demos.common.hashers import base, bcrypt, pbkdf2, scrypt


def _get_hashers(hasher):
    for hasher in hasher.__subclasses__():
        if getattr(hasher, 'algorithm', None):
            yield hasher
        for hasher in _get_hashers(hasher):
            yield hasher


_hashers = {hasher.algorithm: hasher for hasher in _get_hashers(base.BaseHasher)}

def get_hasher(conf):
    return _hashers[conf.key_derivation_algorithm](conf)

