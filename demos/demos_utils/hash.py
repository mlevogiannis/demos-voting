# File: hash.py

import hashlib

from os import urandom
from base64 import b64encode, b64decode

from demos_utils.settings import *


def create_hash(value):
	
	if isinstance(value, str):
		value = value.encode()
	
	h = hashlib.new(HASH_ALG_NAME)
	salt = urandom(HASH_SALT_LEN)
	
	for _ in range(HASH_ITERATIONS):
		h.update(salt + value)
		value = h.digest()
	
	return b64encode(salt + value)


def verify_hash(value, hash_value):
	
	if isinstance(value, str):
		value = value.encode()
	
	h = hashlib.new(HASH_ALG_NAME)
	hash_value = b64decode(hash_value)
	
	salt = hash_value[:HASH_SALT_LEN]
	hash_value = hash_value[HASH_SALT_LEN:]
	
	for _ in range(HASH_ITERATIONS):
		h.update(salt + value)
		value = h.digest()
	
	return hash_value == value

