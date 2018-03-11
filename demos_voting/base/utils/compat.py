from __future__ import absolute_import, division, print_function, unicode_literals

from six.moves import range

try:
    int_to_bytes = int.to_bytes
except AttributeError:
    # https://bugs.python.org/msg177208
    def int_to_bytes(n, length, byteorder, signed=False):
        assert signed is False
        index_iter = range(length)
        if byteorder == 'big':
            index_iter = reversed(index_iter)
        bytes_iter = ((n >> 8 * i) & 0xff for i in index_iter)
        return memoryview(bytearray(bytes_iter)).tobytes()

try:
    int_from_bytes = int.from_bytes
except AttributeError:
    # https://bugs.python.org/msg190004
    def int_from_bytes(bytes, byteorder, signed=False):
        bytes_iter = bytearray(bytes)
        if byteorder == 'big':
            bytes_iter = reversed(bytes_iter)
        n = sum(b << 8 * i for i, b in enumerate(bytes_iter))
        if signed and bytes_iter and (bytes_iter[-1] & 0x80):
            n -= 1 << 8 * len(bytes_iter)
        return n
