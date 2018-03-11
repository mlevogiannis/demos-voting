from __future__ import absolute_import, division, print_function, unicode_literals


def generate_check_character(string, chars):
    """
    Luhn mod N algorithm.
    https://en.wikipedia.org/wiki/Luhn_mod_N_algorithm#Algorithm
    """
    n = len(chars)
    s = sum(sum(divmod(2 * chars.index(c), n)) for c in string[::-2]) + sum(chars.index(c) for c in string[-2::-2])
    return chars[(n - (s % n)) % n]
