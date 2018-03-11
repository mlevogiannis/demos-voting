from __future__ import absolute_import, division, print_function, unicode_literals

try:
    from .local import *
except ImportError:
    from .production import *
