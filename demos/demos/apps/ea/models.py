# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import random
import OpenSSL

from django.apps import apps
from django.db import models
from django.utils import six
from django.utils.encoding import force_bytes
from django.utils.six.moves import range

from demos.common.models import base
from demos.common.utils import base32, crypto, fields

logger = logging.getLogger(__name__)
random = random.SystemRandom()

app_config = apps.get_app_config('ea')
settings = app_config.get_constants_and_settings()


class Election(base.Election):
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_modified_at = models.DateTimeField(auto_now=True)
    
    setup_started_at = models.DateTimeField(null=True, default=None)
    setup_ended_at = models.DateTimeField(null=True, default=None)
    
    def generate_pkey(self):
        
        self.pkey = OpenSSL.crypto.PKey()
        self.pkey.generate_key(OpenSSL.crypto.TYPE_RSA, self.conf.rsa_pkey_bits)
    
    def generate_cert(self):
        
        self.cert = OpenSSL.crypto.X509()
        
        if settings.CA_PKEY_PEM or settings.CA_CERT_PEM:
            
            with open(settings.CA_PKEY_PEM, 'r') as ca_pkey_file:
                ca_pkey = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, ca_pkey_file.read(),
                                                         force_bytes(settings.CA_PKEY_PASSPHRASE))
            
            with open(settings.CA_CERT_PEM, 'r') as ca_cert_file:
                ca_cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, ca_cert_file.read())
            
            self.cert.set_subject(ca_cert.get_subject())
            
        else: # self-signed certificate
            
            ca_cert = self.cert
            ca_pkey = self.pkey
        
        self.cert.get_subject().CN = 'DemosVoting | Election ID: %s' % self.id
        self.cert.set_issuer(ca_cert.get_subject())
        self.cert.set_version(3)
        self.cert.set_serial_number(base32.decode(self.id))
        self.cert.set_notBefore(force_bytes(self.starts_at.strftime('%Y%m%d%H%M%S%z')))
        self.cert.set_notAfter(force_bytes(self.ends_at.strftime('%Y%m%d%H%M%S%z')))
        self.cert.set_pubkey(self.pkey)
        
        self.cert.sign(ca_pkey, str(self.conf.hash_algorithm))


class QuestionC(base.QuestionC):
    pass


class OptionC(base.OptionC):
    pass


class Ballot(base.Ballot):
    
    def generate_credential(self):
        
        randint = random.getrandbits(self.conf.credential_bits)
        
        self.credential = base32.encode(randint, (self.conf.credential_bits + 4) // 5)
        self.credential_hash = self.election.hasher.encode(self.credential)


class Part(base.Part):
    
    def generate_security_code(self):
        
        randint = random.getrandbits(self.conf.security_code_len * 5)
        
        self.security_code = base32.encode(randint, self.conf.security_code_len)
        self.security_code_hash = self.election.hasher.encode(self.security_code)


class QuestionV(base.QuestionV):
    
    def generate_common(self):
        
        if self.election.votecode_type_is_long:
            self.salt = self.election.hasher.salt()
            self.params = self.election.hasher.params()
        else:
            self._short_votecodes = list(range(1, self.options_cnt + 1))
            random.shuffle(self._short_votecodes)


class OptionV(base.OptionV):
    
    decom = fields.ProtoField(cls=crypto.Decom)
    zk_state = fields.ProtoField(cls=crypto.ZKState)
    
    def _generate_short_votecode(self):
        
        votecode = self.question._short_votecodes[self.index]
        return six.text_type(votecode).zfill(self.short_votecode_len)
    
    def generate_votecode(self):
        
        if self.election.votecode_type_is_long:
            
            hasher = self.election.hasher
            salt = self.question.votecode_hash_salt
            params = self.question.votecode_hash_params
            
            self.votecode = self._generate_long_votecode()
            self.votecode_hash = hasher.split(hasher.encode(self.votecode, salt, params))[2]
            
        else:
            self.votecode = self._generate_short_votecode()
    
    def generate_receipt(self):
        
        if self.election.votecode_type_is_long:
            data = self.votecode
        else:
            # A receipt is always the signature of a long votecode, but this
            # option only has a short one. Generate its long votecode here.
            data = self._generate_long_votecode()
        
        signature = OpenSSL.crypto.sign(self.election.pkey, data, str(self.conf.hash_algorithm))
        
        self.receipt_full = base32.encode_from_bytes(signature, (self.conf.rsa_pkey_bits + 4) // 5)
        self.receipt = self.receipt_full[-self.conf.receipt_len:]


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

