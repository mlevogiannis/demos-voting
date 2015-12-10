# File: context_processors.py

from __future__ import absolute_import, division, unicode_literals

import inspect

from demos.common.utils import enums

_predicate = lambda cls: inspect.isclass(cls) and \
    issubclass(cls, enums.IntEnum) and cls != enums.IntEnum

_enum_context = { enumName: { attr.name: attr.value for attr in enumClass }
    for enumName, enumClass in inspect.getmembers(enums, _predicate) }

def common(request):
    return _enum_context

