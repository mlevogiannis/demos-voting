# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import random
import OpenSSL

from django.apps import apps
from django.db import models
from django.utils import six
from django.utils.encoding import force_bytes
from django.utils.functional import cached_property
from django.utils.six.moves import range, zip

from demos.common.models import base
from demos.common.utils import base32cf, crypto, fields

logger = logging.getLogger(__name__)
random = random.SystemRandom()

app_config = apps.get_app_config('ea')
conf = app_config.get_constants_and_settings()


class Election(base.Election):
    
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    setup_started_at = models.DateTimeField(null=True, default=None)
    setup_finished_at = models.DateTimeField(null=True, default=None)
    
    def generate_pkey_and_cert(self):
        
        if conf.CA_PKEY_PEM or conf.CA_CERT_PEM:
            
            self_signed = False
            
            with open(conf.CA_PKEY_PEM, 'r') as ca_pkey_file:
                ca_pkey = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, ca_pkey_file.read(),
                                                         force_bytes(conf.CA_PKEY_PASSPHRASE))
            
            with open(conf.CA_CERT_PEM, 'r') as ca_cert_file:
                ca_cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, ca_cert_file.read())
            
        else:
            self_signed = True
        
        self.pkey = OpenSSL.crypto.PKey()
        self.pkey.generate_key(OpenSSL.crypto.TYPE_RSA, self.conf.rsa_pkey_bits)
        
        self.cert = OpenSSL.crypto.X509()
        
        if not self_signed:
            self.cert.set_subject(ca_cert.get_subject())
        
        self.cert.get_subject().CN = self.name[:64]
        
        issuer_cert = self.cert if self_signed else ca_cert
        self.cert.set_issuer(issuer_cert.get_subject())
        
        self.cert.set_version(3)
        self.cert.set_serial_number(base32cf.decode(self.id))
        
        self.cert.set_notBefore(force_bytes(self.starts_at.strftime('%Y%m%d%H%M%S%z')))
        self.cert.set_notAfter(force_bytes(self.ends_at.strftime('%Y%m%d%H%M%S%z')))
        
        self.cert.set_pubkey(self.pkey)
        
        issuer_pkey = self.pkey if self_signed else ca_pkey
        self.cert.sign(issuer_pkey, str(self.conf.hash_algorithm))


class QuestionC(base.QuestionC):
    pass


class OptionC(base.OptionC):
    pass


class Ballot(base.Ballot):
    
    def generate_credential(self):
        
        conf = self.election.conf
        hasher = self.election.hasher
        
        randint = random.getrandbits(conf.credential_bits)
        
        self.credential = base32cf.encode(randint, (conf.credential_bits + 4) // 5)
        self.credential_hash = hasher.encode(self.credential)


class Part(base.Part):
    
    def generate_security_code(self):
        
        conf = self.election.conf
        hasher = self.election.hasher
        
        randint = random.getrandbits(conf.security_code_len * 5)
        
        self.security_code = base32cf.encode(randint, conf.security_code_len)
        self.security_code_hash = hasher.encode(self.security_code)


class QuestionV(base.QuestionV):
    
    def generate_salt_and_params(self):
        
        if self.election.long_votecodes:
            self.hasher_salt = self.election.hasher.salt()
            self.hasher_params = self.election.hasher.params()
    
    def _get_short_votecode_by_index(self, index):
        
        if not hasattr(self, '_short_votecodes'):
            
            votecodes = list(range(1, self.options_cnt + 1))
            random.shuffle(votecodes)
            
            width = len(six.text_type(self.options_cnt))
            self._short_votecodes = [six.text_type(vc).zfill(width) for vc in votecodes]
        
        return self._short_votecodes[index]


class OptionV(base.OptionV):
    
    decom = fields.ProtoField(cls=crypto.Decom)
    zk_state = fields.ProtoField(cls=crypto.ZKState)
    
    def generate_votecode(self):
        
        if self.election.long_votecodes:
            
            votecode = self._long_votecode()
            
            hasher = self.election.hasher
            encoded = hasher.encode(votecode, self.question.hasher_salt, self.question.hasher_params)
            
            self.votecode = votecode
            self.votecode_hash = hasher.split(encoded)[2]
            
        else:
            self.votecode = self.question._get_short_votecode_by_index(self.index)
    
    def generate_receipt(self):
        
        conf = self.election.conf
        
        data = self._long_votecode() if self.election.short_votecodes else self.votecode
        signature = OpenSSL.crypto.sign(self.election.pkey, data, str(conf.hash_algorithm))
        
        self.receipt_full = base32cf.encode_from_bytes(signature, (conf.rsa_pkey_bits + 4) // 5)
        self.receipt = self.receipt_full[-conf.receipt_len:]


class Trustee(base.Trustee):
    pass


class Conf(base.Conf):
    pass


class Task(base.Task):
    pass


# Common models ----------------------------------------------------------------

from demos.common.utils.api import RemoteUserBase

class RemoteUser(RemoteUserBase):
    pass

