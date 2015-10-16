# File: tests.py

from os import urandom
from random import randrange

from django.test import TestCase

from demos.common.utils import base32cf


class Base32TestCase(TestCase):
	
	def test(self):
		number = int.from_bytes(urandom(4), 'big')
		encoded_number = base32cf.encode(number)
		decoded_number = base32cf.decode(encoded_number)
		assert decoded_number == number

