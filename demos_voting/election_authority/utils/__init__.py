from __future__ import absolute_import, division, print_function, unicode_literals

import math


def permute(input_list, perm_index):
    input_list = list(input_list)
    perm_count = math.factorial(len(input_list))

    if perm_index < 0 or perm_index >= perm_count:
        raise ValueError

    output_list = []
    while input_list:
        perm_count //= len(input_list)
        item_index, perm_index = divmod(perm_index, perm_count)
        item = input_list.pop(item_index)
        output_list.append(item)

    return output_list
