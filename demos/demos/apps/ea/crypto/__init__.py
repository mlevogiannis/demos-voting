# File: __init__.py

from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import socket

from django.conf import settings
from django.utils import six
from django.utils.six.moves import zip

from google.protobuf.descriptor import FieldDescriptor

from .crypto_pb2 import CryptoRequest, CryptoResponse
from .crypto_pb2 import Com, Decom, Key, ZK1, ZK2, ZKState
from demos.common.utils.int import int_from_bytes, int_to_bytes

# crypto_pb2.py:
# DST_DIR="$(realpath ../../../../)"
# SRC_DIR="$DST_DIR/$(realpath --relative-to=$DST_DIR .)"
# protoc --proto_path="$DST_DIR" --python_out="$DST_DIR" "$SRC_DIR/crypto.proto"


af = getattr(socket, settings.DEMOS_CRYPTO_AF)
addr = settings.DEMOS_CRYPTO_ADDR
recv_max = getattr(settings, 'DEMOS_CRYPTO_RECV_MAX', 134217728)   # 128 MB
recv_timeout = getattr(settings, 'DEMOS_CRYPTO_RECV_TIMEOUT', 900)   # 15 mins


_cmd_fields = {
    CryptoRequest.KeyGen: ('kg', 'key'),
    CryptoRequest.GenBallot: ('gb', 'ballot_data'),
    CryptoRequest.AddCom: ('ac', 'combined_com'),
    CryptoRequest.AddDecom: ('ad', 'combined_decom'),
    CryptoRequest.CompleteZK: ('cz', 'zk_set'),
    CryptoRequest.VerifyCom: ('vc', 'check'),
}


def _server_exec(cmd, req_data):
    
    req_field, res_field = _cmd_fields[cmd]
    
    request = CryptoRequest()
    _proto_from_dict(request, {'cmd': cmd, req_field: req_data})
    
    req_data = request.SerializeToString()
    req_size = int_to_bytes(len(req_data), 4, 'big')
    
    sock = socket.socket(af)
    sock.settimeout(recv_timeout)
    sock.connect(addr)
    
    sock.sendall(req_size + req_data)
    sock.shutdown(socket.SHUT_WR)
    
    res_size = int_from_bytes(_recvall(sock, 4), 'big')
    
    if res_size < 1 or res_size > recv_max:
        raise RuntimeError("demos-crypto: response size out of range")
    
    res_data = _recvall(sock, res_size)
    
    sock.shutdown(socket.SHUT_RD)
    sock.close()
    
    response = CryptoResponse()
    response.ParseFromString(res_data)
    
    if not response.HasField(res_field):
        raise RuntimeError("demos-crypto: invalid response")
    
    pb_dict = collections.OrderedDict()
    _proto_to_dict(response, pb_dict)
    
    return pb_dict[res_field]


def _recvall(sock, bufsize):
    
    buf = six.binary_type()
    
    while len(buf) < bufsize:
        val = sock.recv(bufsize - len(buf));
        if not val:
            raise RuntimeError("demos-crypto: connection closed")
        buf += val
        
    return buf


def _proto_to_dict(pb, pb_dict):
    
    for field, value in pb.ListFields():
        
        if field.type is FieldDescriptor.TYPE_MESSAGE:
            if field.label == FieldDescriptor.LABEL_REPEATED:
                new_value = [type(pb_dict)() for v in value]
                for v, new_v in zip(value, new_value):
                    _proto_to_dict(v, new_v)
            else:
                new_value = type(pb_dict)()
                _proto_to_dict(value, new_value)
        else:
            if field.label == FieldDescriptor.LABEL_REPEATED:
                new_value = list(value)
            else:
                new_value = value
        
        pb_dict[field.name] = new_value


def _proto_from_dict(pb, pb_dict):
    
    for key in pb_dict:
        
        field = pb.DESCRIPTOR.fields_by_name[key]
        value = getattr(pb, key)
        
        if field.type == FieldDescriptor.TYPE_MESSAGE:
            if field.label == FieldDescriptor.LABEL_REPEATED:
                for v in pb_dict[key]:
                    _proto_from_dict(value.add(), v)
            else:
                _proto_from_dict(value, pb_dict[key])
        else:
            if field.label == FieldDescriptor.LABEL_REPEATED:
                value.extend(pb_dict[key])
            else:
                setattr(pb, key, pb_dict[key])

# ----------------------------------------------------------------------------


def generate_key(curve):
    
    cmd = CryptoRequest.KeyGen
    
    req_data = {
        'curve': curve,
    }
    
    return _server_exec(cmd, req_data)


def generate_ballots(key, options, blanks, number):
    
    cmd = CryptoRequest.GenBallot
    
    req_data = {
        'key': key,
        'options': options,
        'blanks': blanks,
        'number': 2 * number,
    }
    
    res_data = _server_exec(cmd, req_data)
    
    opts = [[[(opt['com'], opt['decom'], opt['zk1'], opt['zk_state']) for opt in part['opt']]
            for part in ballot if 'opt' in part] for ballot in zip(*[iter(res_data['ballot'])] * 2)]
    
    blks = [[[(blk['com'], blk['decom'], blk['zk1'], blk['zk_state']) for blk in part['blank']]
            for part in ballot if 'blank' in part] for ballot in zip(*[iter(res_data['ballot'])] * 2)]
    
    return (opts, blks)


def add_com(key, com_list):
    
    cmd = CryptoRequest.AddCom
    
    req_data = {
        'key': key,
        'com': com_list,
    }
    
    return _server_exec(cmd, req_data)


def add_decom(key, decom_list):
    
    cmd = CryptoRequest.AddDecom
    
    req_data = {
        'key': key,
        'decom': decom_list,
    }
    
    return _server_exec(cmd, req_data)


def complete_zk(key, options, coins, zk_list):
    
    cmd = CryptoRequest.CompleteZK
    
    req_data = {
        'key': key,
        'options': options,
        'coins': coins,
        'zk_set': [{'zk1': zk1, 'zk_state': zk_state} for zk1, zk_state in zk_list]
    }
    
    return _server_exec(cmd, req_data)['zk2']


def verify_com(key, com, decom):
    
    cmd = CryptoRequest.VerifyCom
    
    req_data = {
        'key': key,
        'com': com,
        'decom': decom,
    }
    
    return _server_exec(cmd, req_data)

