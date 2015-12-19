# File: __init__.py

from __future__ import absolute_import, division, unicode_literals

from demos.common.conf import constants
from demos.common.hashers import base, bcrypt, pbkdf2, scrypt


class _ConstantsConf(object):
    def __getattr__(self, name):
        return getattr(constants, name.upper())


def _get_hashers(hasher):
    for hasher in hasher.__subclasses__():
        if getattr(hasher, 'algorithm', None):
            yield hasher
        for hasher in _get_hashers(hasher):
            yield hasher


_constants = _ConstantsConf()
_hashers = {hasher.algorithm: hasher for hasher in _get_hashers(base.BaseHasher)}

def get_hasher(conf=_constants):
    return _hashers[conf.key_derivation](conf)

