# File: json.py

import json

from base64 import b64encode
from google.protobuf import message
from django.core.serializers.json import DjangoJSONEncoder


class CustomJSONEncoder(DjangoJSONEncoder):
    """JSONEncoder subclass that supports date/time and protobuf types."""
    
    def default(self, o):
        
        if isinstance(o, message.Message):
            r = o.SerializeToString()
            r = b64encode(r).decode('ascii')
            return r
        
        return super(CustomJSONEncoder, self).default(o)
