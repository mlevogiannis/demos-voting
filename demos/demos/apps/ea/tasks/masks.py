# File: masks.py

from __future__ import absolute_import, division, unicode_literals

import re

_masks = {
    
    'bds' : {
        'Election': ['id', 'state', 'type', 'vc_type', 'name', 'starts_at',
            'ends_at', 'ballot_cnt'],
        'Ballot': ['serial'],
        'Part': ['index', 'security_code', 'voter_token'],
     },
    
    'abb' : {
        'Election': ['id', 'state', 'type', 'vc_type', 'name', 'starts_at',
            'ends_at', 'ballot_cnt'],
        'Question': ['text', 'key', 'index', 'option_cnt', 'choices'],
        'OptionC': ['text', 'index'],
        'Ballot': ['serial', 'credential_hash'],
        'Part': ['index', 'security_code_hash2', 'l_votecode_salt',
            'l_votecode_iterations'],
        'OptionV' : ['votecode', 'l_votecode_hash', 'com', 'zk1', 'index',
            'question', 'receipt_full'],
     },
    
    'vbb' : {
        'Election': ['id', 'state', 'type', 'vc_type', 'name', 'starts_at',
            'ends_at', 'ballot_cnt'],
        'Question': ['text', 'index', 'option_cnt', 'columns', 'choices'],
        'OptionC': ['text', 'index'],
        'Ballot': ['serial', 'credential_hash'],
        'Part': ['index', 'security_code_hash2', 'l_votecode_salt',
            'l_votecode_iterations'],
        'OptionV' : ['votecode', 'l_votecode_hash', 'receipt', 'index',
            'question'],
     },
}

_mask_list_re = re.compile('^__list_(.+)__$')


def _apply_mask(obj, app_mask, model_mask):
    
    result = {}
    
    for key, value in obj.items():
        
        if key in model_mask:
            result[key] = value
        
        else:
            match = _mask_list_re.search(key)
            if match:
                model = match.group(1)
                if model in app_mask:
                    result[key] = [_apply_mask(_obj, app_mask, app_mask[model]) for _obj in value]
    
    return result


def apply_mask(app, obj, model='Election'):
    return _apply_mask(obj, _masks[app], _masks[app][model])

