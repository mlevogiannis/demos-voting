# File: enums.py

from __future__ import division

from enum import IntEnum, unique


# workaround for python2

import six

if six.PY2:
    class IntEnum(IntEnum):
        def __str__(self):
            return str(int(self))

# end of workaround


@unique
class State(IntEnum):
    
    DRAFT = 1
    PENDING = 2
    WORKING = 3
    RUNNING = 4
    COMPLETED = 5
    PAUSED = 6
    ERROR = 7
    TEMPLATE = 8

