# File: enums.py

from __future__ import division

from enum import IntEnum, unique


# workaround for json encoder bug in python < 3.4
# reference: https://bugs.python.org/issue18264

import sys

if sys.version_info[0:2] < (3,4):
    
    class IntEnum(IntEnum):
        def __str__(self):
            return str(int(self))


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

