# File: cryptotools.py

from __future__ import absolute_import, division, unicode_literals

import socket

from django.apps import apps
from django.utils.six.moves import zip

from demos.common.utils import crypto, intc

app_config = apps.get_app_config('ea')
conf = app_config.get_constants_and_settings()


def gen_key(curve):
    
    req = crypto._CryptoRequest()
    req.cmd = crypto._CryptoRequest.KeyGen
    
    req.kg.curve = curve
    
    res = _request_to_response(req, "key")
    return res.key


def gen_ballot(key, options, blanks, number):
    
    req = crypto._CryptoRequest()
    req.cmd = crypto._CryptoRequest.GenBallot
    
    req.gb.key.CopyFrom(key)
    req.gb.options = options
    req.gb.blanks = blanks
    req.gb.number = 2 * number
    
    res = _request_to_response(req, "ballot_data")
    
    opts = [[[(opt.com, opt.decom, opt.zk1, opt.zk_state) for opt in part.opt]
    for part in ballot] for ballot in zip(*[iter(res.ballot_data.ballot)] * 2)]
    
    blks = [[[(blk.com, blk.decom, blk.zk1, blk.zk_state) for blk in part.blank]
    for part in ballot] for ballot in zip(*[iter(res.ballot_data.ballot)] * 2)]
    
    return (opts, blks)


def add_com(key, com_list):
    
    req = crypto._CryptoRequest()
    req.cmd = crypto._CryptoRequest.AddCom
    
    req.ac.key.CopyFrom(key)
    req.ac.com.extend(com_list)
    
    res = _request_to_response(req, "combined_com")
    return res.combined_com


def add_decom(key, decom_list):
    
    req = crypto._CryptoRequest()
    req.cmd = crypto._CryptoRequest.AddDecom
    
    req.ad.key.CopyFrom(key)
    req.ad.decom.extend(decom_list)
    
    res = _request_to_response(req, "combined_decom")
    return res.combined_decom


def complete_zk(key, options, coins, zk_list):
    
    req = crypto._CryptoRequest()
    req.cmd = crypto._CryptoRequest.CompleteZK
    
    req.cz.key.CopyFrom(key)
    req.cz.options = options
    req.cz.coins = coins
    
    for zk1, zk_state in zk_list:
        zk_set = req.cz.zk_set.add()
        zk_set.zk1.CopyFrom(zk1)
        zk_set.zk_state.CopyFrom(zk_state)
    
    res = _request_to_response(req, "zk_set")
    return list(res.zk_set.zk2)


def verify_com(key, com, decom):
    
    req = crypto._CryptoRequest()
    req.cmd = crypto._CryptoRequest.VerifyCom
    
    req.vc.key.CopyFrom(key)
    req.vc.com.CopyFrom(com)
    req.vc.decom.CopyFrom(decom)
    
    res = _request_to_response(req, "check")
    return res.check


def _request_to_response(request, response_field):
    
    data = request.SerializeToString()
    size = intc.to_bytes(len(data), 4, 'big')
    
    af = getattr(socket, conf.CRYPTO_AF)
    sock = socket.socket(af)
    
    sock.settimeout(conf.RECV_TIMEOUT)
    sock.connect(conf.CRYPTO_ADDR)
    
    sock.sendall(size + data)
    sock.shutdown(socket.SHUT_WR)
    
    size = _recvall(sock, 4)
    size = intc.from_bytes(size, 'big')
    
    if size < 1 or size > conf.RECV_MAX:
        raise RuntimeError("demos-crypto: response size out of range")
        
    data = _recvall(sock, size)
    sock.shutdown(socket.SHUT_RD)
    
    sock.close()
    
    response = crypto._CryptoResponse()
    response.ParseFromString(data)
    
    if not response.HasField(response_field):
        raise RuntimeError("demos-crypto: invalid response")
    
    return response


def _recvall(sock, bufsize):
    
    buf = bytes()
    
    while len(buf) < bufsize:
        
        ret = sock.recv(bufsize - len(buf));
        if not ret:
            raise RuntimeError("demos-crypto: connection closed")
        buf += ret
    
    return buf

