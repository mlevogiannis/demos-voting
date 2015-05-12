# File: settings.py

import math
import hashlib

from django.conf import settings

DEMOS_SETTINGS = getattr(settings, 'DEMOS_SETTINGS')

# Required settings ------------------------------------------------------------

URL = {}

URL['ea'] = DEMOS_SETTINGS.get('EA_URL')
URL['bds'] = DEMOS_SETTINGS.get('BDS_URL')
URL['abb'] = DEMOS_SETTINGS.get('ABB_URL')
URL['vbb'] = DEMOS_SETTINGS.get('VBB_URL')

PRE_SHARED_KEY = DEMOS_SETTINGS.get('PRE_SHARED_KEY').encode()

# EA-only required settings

CRYPTO_AF = DEMOS_SETTINGS.get('CRYPTO_AF')
CRYPTO_ADDR = DEMOS_SETTINGS.get('CRYPTO_ADDR')


# Optional settings ------------------------------------------------------------

TEXT_LEN = DEMOS_SETTINGS.get('TEXT_LEN', 128)

QUESTIONS_MAX = DEMOS_SETTINGS.get('QUESTIONS_MAX', 16)
BALLOTS_MAX = DEMOS_SETTINGS.get('BALLOTS_MAX', 65535)
OPTIONS_MAX = DEMOS_SETTINGS.get('OPTIONS_MAX', 64)
TRUSTEES_MAX = DEMOS_SETTINGS.get('TRUSTEES_MAX', 128)

DATETIME_FORMAT = DEMOS_SETTINGS.get('DATETIME_FORMAT', '%d/%m/%Y %H:%M')


# Advanced settings ------------------------------------------------------------

BATCH_SIZE = DEMOS_SETTINGS.get('BATCH_SIZE', 128)

RECV_MAX = DEMOS_SETTINGS.get('RECV_MAX', 67108864)   # 64 MB
RECV_TIMEOUT = DEMOS_SETTINGS.get('RECV_TIMEOUT', 900)   # 15 mins


# Static configuration, do not override ----------------------------------------

LANGUAGES = getattr(settings, 'LANGUAGES')

SIDE_ID_LIST = sorted(('A', 'B'))   # single utf-8 characters only
SIDE_ID_CHOICES = tuple(zip(SIDE_ID_LIST, SIDE_ID_LIST))

BALLOT_ID_BYTES = math.ceil(BALLOTS_MAX.bit_length() / 8)
SIDE_ID_BYTES = max([len(side_id.encode()) for side_id in SIDE_ID_LIST])

CREDENTIAL_BYTES = 8

# Base32-encoded

RECEIPT_LEN = 6
PERMINDEX_LEN = 8

def _rand_calc(length, base):
	bits = math.floor(math.log2(base ** length))
	bytes = math.ceil(bits / 8)
	shift_bits = (8 * bytes) - bits
	return (bytes, shift_bits)

RECEIPT_BYTES, RECEIPT_SHIFT_BITS = _rand_calc(RECEIPT_LEN, 32)
PERMINDEX_BYTES, PERMINDEX_SHIFT_BITS = _rand_calc(PERMINDEX_LEN, 32)

VOTEURL_LEN = math.ceil((8/5) * (BALLOT_ID_BYTES + CREDENTIAL_BYTES + \
	SIDE_ID_BYTES + (len(SIDE_ID_LIST)-1) * PERMINDEX_BYTES))

# Base64-encoded

HASH_ALG_NAME = 'sha256'

HASH_SALT_LEN = 16
HASH_ITERATIONS = 2

HASH_DIGEST_LEN = hashlib.new(HASH_ALG_NAME).digest_size
HASH_LEN = int(math.ceil(((4/3) * (HASH_DIGEST_LEN + HASH_SALT_LEN)) / 4) * 4)

# Convert python's datetime format to momentjs' datetime format. Supported
# directives are %d, %m, %y, %Y, %H, %M and %S. For more information, see:
# https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior
# http://momentjs.com/docs/#/displaying/format/

def _datetime_py2js(datetime_format):
	
	conv_dict = {
		'%d': 'DD',
		'%m': 'MM',
		'%y': 'YY',
		'%Y': 'YYYY',
		'%H': 'HH',
		'%M': 'mm',
		'%S': 'ss',
	}
	
	for py, js in conv_dict.items():
		datetime_format = datetime_format.replace(py, js)
	
	return datetime_format

DATETIME_FORMAT_JS = _datetime_py2js(DATETIME_FORMAT)

