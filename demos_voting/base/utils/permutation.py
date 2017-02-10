# File: permutation.py

from __future__ import absolute_import, division, print_function, unicode_literals

import math


def permutation(initial, index):

    initial = list(initial)
    factorial = math.factorial(len(initial))

    if index < 0 or index >= factorial:
        raise ValueError

    final = []
    while initial:
        factorial //= len(initial)
        item, index = divmod(index, factorial)
        final.append(initial.pop(item))

    return final
