# File: permutations.py

from math import factorial


def permutation(iterable, index):
	
	seq = list(iterable)
	fact = factorial(len(seq))
	index %= fact
	perm = []
	
	while seq:
		fact //= len(seq)
		next, index = divmod(index, fact)
		item = seq.pop(next)
		perm.append(item)
	
	return perm

