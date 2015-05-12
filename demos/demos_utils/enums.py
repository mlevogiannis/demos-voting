# File: enums.py

from enum import IntEnum, unique


@unique
class State(IntEnum):
	
	WORKING = 1    # Election is being created
	STARTED = 2    # Election is started (intersection with datetimes)
	STOPPED = 3    # Election is (temporarily) stopped
	SUCCESS = 4    # Election completed successfully
	FAILURE = 5    # Election creation or verification failed
	INVALID = 6    # Election is invalid (not an actual state)

