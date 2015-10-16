# File: enums.py

from enum import IntEnum, unique

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

