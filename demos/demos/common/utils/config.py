# File: config.py

from __future__ import division

TITLE_MAXLEN = 128    # chars
OPTION_MAXLEN = 128    # chars
QUESTION_MAXLEN = 128   # chars

RECEIPT_LEN = 10  # base32
VOTECODE_LEN = 16   # base32
CREDENTIAL_LEN = 8    # bytes
SECURITY_CODE_LEN = 8   # base32

HASH_LEN = 128   # chars

PKEY_BIT_LEN = 2048   # bits
PKEY_PASSPHRASE_LEN = 32   # base64
PKEY_PASSPHRASE_CIPHER = 'AES-128-CBC'  # openssl list-cipher-algorithms

# ------------------------------------------------------------------------------

import sys
from django.conf import settings

_config = sys.modules[__name__]

for iapp in settings.DEMOS_APPS:
    for key, value in settings.DEMOS_CONFIG[iapp].items():
        setattr(_config, key, value)

