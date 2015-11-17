# File: protobuf.py

from __future__ import division, unicode_literals

from collections import OrderedDict
from google.protobuf.descriptor import FieldDescriptor


def to_dict(pb, ordered=False):
    
    pb_dict = OrderedDict() if ordered else {}
    
    for field, value in pb.ListFields():
        
        if field.type is FieldDescriptor.TYPE_MESSAGE:
            
            if field.label == FieldDescriptor.LABEL_REPEATED:
                value = [to_dict(val) for val in value]
            else:
                value = to_dict(value)
            
        else:
            
            if field.label == FieldDescriptor.LABEL_REPEATED:
                value = list(value)
        
        pb_dict[field.name] = value
        
    return pb_dict


def from_dict(pb, pb_dict):
    
    for key in pb_dict:
        
        field = pb.DESCRIPTOR.fields_by_name[key]
        value = getattr(pb, key)
        
        if field.type == FieldDescriptor.TYPE_MESSAGE:
            
            if field.label == FieldDescriptor.LABEL_REPEATED:
                for val in pb_dict[key]: from_dict(value.add(), val)
            else:
                from_dict(value, pb_dict[key])
            
        else:
            
            if field.label == FieldDescriptor.LABEL_REPEATED:
                value.extend(pb_dict[key])
            else:
                setattr(pb, key, pb_dict[key])

