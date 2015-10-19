# -*- encoding: utf-8 -*-
# File: demos.py

DEMOS_MAIN = ''   # ea, bds, abb, vbb

DEMOS_URL = {
	
	# Server URLs (always include URL scheme and trailing slash)
	
	'ea': '',
	'bds': '',
	'abb': '',
	'vbb': '',
}

DEMOS_CONFIG = {
	
	'ea': {
		
		# Election configuration
		
		'MAX_BALLOTS': 100000,
		'MAX_OPTIONS': 128,
		'MAX_TRUSTEES': 128,
		'MAX_QUESTIONS': 32,
		
		# demos-crypto connection settings, see:
		# https://docs.python.org/3/library/socket.html
		
		'CRYPTO_AF': '',   # e.g.: 'AF_UNIX' or 'AF_INET' or 'AF_INET6'
		'CRYPTO_ADDR': '',   # e.g.: '/tmp/demos.sock' or ('127.0.0.1', 8999)
		
		# Performance settings, they affect CPU and RAM usage, etc
		
		'BATCH_SIZE': 128,
		
		'RECV_MAX': 67108864,   # 64 MB
		'RECV_TIMEOUT': 900,   # 15 mins
	},
	
	'bds': {
		
		# Absolute filesystem path to the directory that will hold tar files.
		# They are used to organize PDF ballot files by their election ID.
		
		'TARSTORAGE_ROOT': '',
		
		# URL that handles the files served from TARSTORAGE_ROOT. If this is
		# None, files will not be accessible via an URL.
		
		'TARSTORAGE_URL': None,
		
		# The numeric mode (i.e. 0x644) to set root tar files to. If this is
		# None, you’ll get operating-system dependent behavior.
		
		'TARSTORAGE_PERMISSIONS': None,
	},
	
	'abb': {
	},
	
	'vbb': {
	},
}
