# File: hashers.py

from django.utils.crypto import constant_time_compare
from django.contrib.auth.hashers import PBKDF2PasswordHasher

class CustomPBKDF2PasswordHasher(PBKDF2PasswordHasher):
	"""A subclass of PBKDF2PasswordHasher that uses less iterations."""
	
	iterations = 1000
	algorithm = "_pbkdf2"
	
	def verify_list(self, password, encoded_list):
		"""Checks if the given password is correct, by searching in a list of
		encoded hashes. Returns the matching hash's index or -1"""
		
		lru_cache = (None, None)
		
		for index, encoded in enumerate(encoded_list):
			
			algorithm, iterations, salt, hash = encoded.split('$', 3)
			assert algorithm == self.algorithm
			
			iterations_c, salt_c = lru_cache
			
			if iterations != iterations_c or salt != salt_c:
				
				lru_cache = (iterations, salt)
				encoded_2 = self.encode(password, salt, int(iterations))
			
			if constant_time_compare(encoded, encoded_2):
				return index
		
		return -1

