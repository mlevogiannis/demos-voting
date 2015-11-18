# File: enums.py

from __future__ import division, unicode_literals

from enum import IntEnum, unique

# workaround for json encoder bug
# see: https://bugs.python.org/issue18264

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

@unique
class Vc(IntEnum):
    
    SHORT = 1
    LONG = 2

