# File: enums.py

try:
    from enum import IntEnum, unique
except ImportError:
    class IntEnum:
        pass
    
    def unique(fn):
        return fn

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

