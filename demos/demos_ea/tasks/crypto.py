# File: crypto.py

import socket

from google.protobuf.descriptor import FieldDescriptor
from demos_ea.tasks import protobuf
from demos_utils.settings import *


class CryptoClient:
	
	def __init__(self, family, address):
		
		self.family = family
		self.address = address
	
	def gen_key(self, ballots, options):
		
		req = protobuf.CryptoRequest()
		
		req.kg.ballots = ballots
		req.kg.options = options
		
		res = self._request_to_response(req, "key")
		return self._to_dict(res.key)
	
	def gen_ballot(self, key, ballots, options, number):
		
		req = protobuf.CryptoRequest()
		
		self._from_dict(req.gb.key, key)
		
		req.gb.ballots = ballots
		req.gb.options = options
		req.gb.number = number * len(SIDE_ID_LIST)
		
		res = self._request_to_response(req, "ballot_data")
		
		return [[(self._to_dict(enc.com), self._to_dict(enc.decom),
			self._to_dict(enc.zk1), self._to_dict(enc.zk_state))
			for enc in ballot.enc] for ballot in res.ballot_data.ballot]
	
	def add_com(self, key, com_list):
		
		req = protobuf.CryptoRequest()
		
		self._from_dict(req.ac.key, key)
		
		for com in com_list:
			req_com = req.ac.com.add()
			self._from_dict(req_com, com)
		
		res = self._request_to_response(req, "added_com")
		return self._to_dict(res.added_com)
	
	def add_decom(self, key, decom_list):
		
		req = protobuf.CryptoRequest()
		
		self._from_dict(req.ad.key, key)
		
		for decom in decom_list:
			req_decom = req.ad.decom.add()
			self._from_dict(req_decom, decom)
		
		res = self._request_to_response(req, "added_decom")
		return self._to_dict(res.added_decom)
	
	def complete_zk(self, key, options, coins, zk_list):
		
		req = protobuf.CryptoRequest()
		
		self._from_dict(req.cz.key, key)
		
		req.cz.options = options
		req.cz.coins = coins
		
		for zk1, zk_state in zk_list:
			zk_set = req.cz.zk_set.add()
			self._from_dict(zk_set.zk1, zk1)
			self._from_dict(zk_set.zk_state, zk_state)
		
		res = self._request_to_response(req, "zk_set")
		return [self._to_dict(zk2) for zk2 in res.zk_set.zk2]
	
	def verify_com(self, key, com, decom):
		
		req = protobuf.CryptoRequest()
		
		self._from_dict(req.vc.key, key)
		self._from_dict(req.vc.com, com)
		self._from_dict(req.vc.decom, decom)
		
		res = self._request_to_response(req, "check")
		return res.check
	
	def _request_to_response(self, request, response_oneof):
		
		data = request.SerializeToString()
		size = len(data).to_bytes(4, 'big')
		
		sock = socket.socket(self.family)
		
		sock.settimeout(float(RECV_TIMEOUT))
		sock.connect(self.address)
		
		sock.sendall(size + data)
		
		size = CryptoClient._recvall(sock, 4)
		size = int.from_bytes(size, 'big')
		
		if size < 1 or size > RECV_MAX:
			raise RuntimeError("CryptoClient: response size out of range")
			
		data = CryptoClient._recvall(sock, size)
		
		sock.shutdown(socket.SHUT_RDWR)
		sock.close()
		
		response = protobuf.CryptoResponse()
		response.ParseFromString(data)
		
		if response.WhichOneof("response") != response_oneof:
			raise RuntimeError("CryptoClient: invalid response")
		
		return response
	
	@staticmethod
	def _recvall(sock, bufsize):
		
		buf = bytes()
		
		while len(buf) < bufsize:
			
			ret = sock.recv(bufsize - len(buf));
			if not ret:
				raise RuntimeError("CryptoClient: connection closed")
			buf += ret
		
		return buf
	
	@staticmethod
	def _to_dict(pb):
		
		pb_dict = {}
		
		for field, value in pb.ListFields():
			
			if field.type is FieldDescriptor.TYPE_MESSAGE:
				
				if field.label == FieldDescriptor.LABEL_REPEATED:
					value = [CryptoClient._to_dict(val) for val in value]
				else:
					value = CryptoClient._to_dict(value)
				
			else:
				
				if field.label == FieldDescriptor.LABEL_REPEATED:
					value = list(value)
			
			pb_dict[field.name] = value
			
		return pb_dict
	
	@staticmethod
	def _from_dict(pb, pb_dict):
		
		for key in pb_dict:
			
			field = pb.DESCRIPTOR.fields_by_name[key]
			value = getattr(pb, key)
			
			if field.type == FieldDescriptor.TYPE_MESSAGE:
				
				if field.label == FieldDescriptor.LABEL_REPEATED:
					for val in pb_dict[key]:
						CryptoClient._from_dict(value.add(), val)
				else:
					CryptoClient._from_dict(value, pb_dict[key])
				
			else:
				
				if field.label == FieldDescriptor.LABEL_REPEATED:
					value.extend(pb_dict[key])
				else:
					setattr(pb, key, pb_dict[key])

