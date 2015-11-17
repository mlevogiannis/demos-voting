# File: cryptotools.py

from __future__ import division, unicode_literals

import socket

from demos.common.utils import crypto, intc
from demos.common.utils.config import registry

config = registry.get_config('ea')


def gen_key(ballots, options):
    
    req = crypto._CryptoRequest()
    req.cmd = crypto._CryptoRequest.KeyGen
    
    req.kg.ballots = ballots
    req.kg.options = options
    
    res = _request_to_response(req, "key")
    return res.key


def gen_ballot(key, ballots, options, number):
    
    req = crypto._CryptoRequest()
    req.cmd = crypto._CryptoRequest.GenBallot
    
    req.gb.key.CopyFrom(key)
    req.gb.ballots = ballots
    req.gb.options = options
    req.gb.number = 2 * number
    
    res = _request_to_response(req, "ballot_data")
    
    return [[[(enc.com, enc.decom, enc.zk1, enc.zk_state) for enc in part.enc]
    for part in ballot] for ballot in zip(*[iter(res.ballot_data.ballot)] * 2)]


def add_com(key, com_list):
    
    req = crypto._CryptoRequest()
    req.cmd = crypto._CryptoRequest.AddCom
    
    req.ac.key.CopyFrom(key)
    req.ac.com.extend(com_list)
    
    res = _request_to_response(req, "added_com")
    return res.added_com


def add_decom(key, decom_list):
    
    req = crypto._CryptoRequest()
    req.cmd = crypto._CryptoRequest.AddDecom
    
    req.ad.key.CopyFrom(key)
    req.ad.decom.extend(decom_list)
    
    res = _request_to_response(req, "added_decom")
    return res.added_decom


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
    
    af = getattr(socket, config.CRYPTO_AF)
    sock = socket.socket(af)
    
    sock.settimeout(config.RECV_TIMEOUT)
    sock.connect(config.CRYPTO_ADDR)
    
    sock.sendall(size + data)
    sock.shutdown(socket.SHUT_WR)
    
    size = _recvall(sock, 4)
    size = intc.from_bytes(size, 'big')
    
    if size < 1 or size > config.RECV_MAX:
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

