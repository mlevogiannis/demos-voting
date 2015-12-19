# File: json.py

from __future__ import absolute_import, division, print_function, unicode_literals

from base64 import b64encode
from django.core.serializers.json import DjangoJSONEncoder
from google.protobuf import message


class CustomJSONEncoder(DjangoJSONEncoder):
    """JSONEncoder subclass that supports date/time and protobuf types."""
    
    def default(self, o):
        
        if isinstance(o, message.Message):
            r = o.SerializeToString()
            r = b64encode(r).decode('ascii')
            return r
        
        return super(CustomJSONEncoder, self).default(o)
