# File: models.py

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import logging
import random
import OpenSSL

from django.conf import settings
from django.db import models
from django.utils import six
from django.utils.encoding import force_bytes
from django.utils.six.moves import range
from django.utils.translation import ugettext_lazy as _

from demos.common.models import base
from demos.common.utils import base32, crypto, fields

logger = logging.getLogger(__name__)
random = random.SystemRandom()



class Election(base.Election):
    
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    modified_at = models.DateTimeField(_("modified at"), auto_now=True)
    setup_started_at = models.DateTimeField(_("setup started at"), null=True, default=None)
    setup_ended_at = models.DateTimeField(_("setup ended at"), null=True, default=None)
    
    def generate_key(self):
        
        self.key = OpenSSL.crypto.PKey()
        self.key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)
    
    def generate_cert(self):
        
        self.cert = OpenSSL.crypto.X509()
        
        ca_pkey_path = getattr(settings, 'DEMOS_CA_PKEY_FILE', '')
        ca_cert_path = getattr(settings, 'DEMOS_CA_CERT_FILE', '')
        
        if ca_pkey_path or ca_cert_path:
            
            ca_pkey_passphrase = getattr(settings, 'DEMOS_CA_PKEY_PASSPHRASE', '')
            
            with open(ca_pkey_path, 'r') as ca_pkey_file:
                ca_key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, ca_pkey_file.read(),
                                                        force_bytes(ca_pkey_passphrase))
            
            with open(ca_cert_path, 'r') as ca_cert_file:
                ca_cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, ca_cert_file.read())
            
            self.cert.set_subject(ca_cert.get_subject())
            
        else: # self-signed certificate
            
            ca_key = self.key
            ca_cert = self.cert
        
        validity_period = datetime.timedelta(365)
        
        self.cert.get_subject().CN = "DEMOS Voting - Election ID: %s" % self.id
        self.cert.set_issuer(ca_cert.get_subject())
        self.cert.set_version(3)
        self.cert.set_serial_number(base32.decode(self.id))
        self.cert.set_notBefore(force_bytes(self.setup_started_at.strftime('%Y%m%d%H%M%S%z')))
        self.cert.set_notAfter(force_bytes((self.setup_started_at+validity_period).strftime('%Y%m%d%H%M%S%z')))
        self.cert.set_pubkey(self.key)
        self.cert.sign(ca_key, str(self.conf.hash_algorithm))


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


class Question(base.Question):
    pass


class Option_P(base.Option_P):
    pass


class Option_C(base.Option_C):
    
    decom = fields.ProtoField(cls=crypto.Decom)
    zk_state = fields.ProtoField(cls=crypto.ZKState)
    
    def generate_votecode(self):
        
        if self.election.votecode_type_is_long:
            hasher = self.election.hasher
            
            salt = self.partquestion.votecode_hash_salt
            params = self.partquestion.votecode_hash_params
            
            self.votecode = self._generate_long_votecode()
            self.votecode_hash_value = hasher.split(hasher.encode(self.votecode, salt, params))[2]
            
        else:
            self.votecode = self.partquestion.short_votecodes[self.index]
    
    def generate_receipt(self):
        
        # The receipt is derived from the option's long votecode. If the
        # election uses short votecodes, a temporary long votecode needs
        # to be generated.
        
        data = self._generate_long_votecode() if self.election.votecode_type_is_short else self.votecode
        signature = OpenSSL.crypto.sign(self.election.key, data, str(self.conf.hash_algorithm))
        
        self.receipt_full = base32.encode_from_bytes(signature, (self.election.key.bits() + 4) // 5)
        self.receipt = self.receipt_full[-self.conf.receipt_len:]


class PartQuestion(base.PartQuestion):
    
    def generate_common(self):
        
        if self.election.votecode_type_is_long:
            self.votecode_hash_salt = self.election.hasher.salt()
            self.votecode_hash_params = self.election.hasher.params()
        else:
            zfill = lambda votecode: six.text_type(votecode).zfill(self.options_c.short_votecode_len)
            self.short_votecodes = list(map(zfill, range(1, self.option_cnt + 1)))
            random.shuffle(self.short_votecodes)


class Task(base.Task):
    pass


# Common models ----------------------------------------------------------------

from demos.common.utils.api import RemoteUserBase

class RemoteUser(RemoteUserBase):
    pass

