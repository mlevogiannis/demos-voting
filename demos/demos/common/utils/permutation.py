# File: permutation.py

from __future__ import division, unicode_literals

import math


def permute(iterable, index):
    
    seq = list(iterable)
    fact = math.factorial(len(seq))
    index %= fact
    perm = []
    
    while seq:
        fact //= len(seq)
        next, index = divmod(index, fact)
        item = seq.pop(next)
        perm.append(item)
    
    return perm


def permute_ori(iterable, index):
    
    seq = list(iterable)
    seqlen = len(seq)
    
    fact = math.factorial(seqlen)
    index %= fact
    
    next = []
    
    for i in range(seqlen, 0, -1):
        fact //= i
        pos, index = divmod(index, fact)
        next.append(pos)
    
    perm = []
    
    for item, pos in zip(reversed(seq), reversed(next)):
        perm.insert(pos, item)
    
    return perm

