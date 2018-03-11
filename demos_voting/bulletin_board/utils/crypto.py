from __future__ import absolute_import, division, print_function, unicode_literals

from base64 import b64decode, b64encode as _b64encode

from django.utils.encoding import force_text

from petlib.bn import Bn
from petlib.ec import EcGroup, EcPt

from six.moves import zip


def b64encode(*args, **kwargs):
    return force_text(_b64encode(*args, **kwargs))


def add_com(commitments, nid=415):
    """
    Add a list of commitments, nid is the curve ID. It returns the combined
    commitment.
    """
    G = EcGroup(nid)
    ec_s1s = []
    ec_s2s = []
    for commitment in commitments:
        if not ec_s1s and not ec_s2s and commitment:
            # Populate the ec_s1 and ec_s2 lists the first time a non-empty
            # commitment is found.
            for i in range(len(commitment)):
                ec_s1s.append(G.infinite())
                ec_s2s.append(G.infinite())
        for i, c in enumerate(commitment):
            ec_s1s[i] += EcPt.from_binary(b64decode(c['C1']), G)
            ec_s2s[i] += EcPt.from_binary(b64decode(c['C2']), G)
    return [
        {'C1': b64encode(ec_s1.export()), 'C2': b64encode(ec_s2.export())}
        for ec_s1, ec_s2 in zip(ec_s1s, ec_s2s)
    ]


def add_decom(decommitments, nid=415):
    """
    Add a list of decommitments, nid is the curve ID. It returns the combined
    decommitment.
    """
    G = EcGroup(nid)
    order = G.order()
    bn_sums = []
    for decommitment in decommitments:
        if not bn_sums and decommitment:
            # Populate the bn_sum list the first time a non-empty decommitment
            # is found.
            for i in range(len(decommitment)):
                bn_sums.append(Bn(0))
        for i, d in enumerate(decommitment):
            bn_sums[i] = bn_sums[i].mod_add(Bn.from_binary(b64decode(d)), order)
    return [b64encode(bn_sum.binary()) for bn_sum in bn_sums]


def extract(h, commitment, decommitment, max_plaintext, nid=415):
    """
    Take the decommitment and brute force the plaintext. h is the public key
    and nid is the curve ID. It returns the plaintexts.
    """
    G = EcGroup(nid)
    ec_g = G.generator()
    ec_h = EcPt.from_binary(b64decode(h), G)
    plaintexts = []
    for c, d in zip(commitment, decommitment):
        ec_c1 = EcPt.from_binary(b64decode(c['C1']), G)
        ec_c2 = EcPt.from_binary(b64decode(c['C2']), G)
        bn_r = Bn.from_binary(b64decode(d))
        if ec_c1 != bn_r * ec_g:
            raise ValueError("Invalid decommitment.")
        ec_temp = ec_c2 - bn_r * ec_h
        ec_sum = G.infinite()
        for i in range(max_plaintext + 1):
            if ec_temp == ec_sum:
                plaintexts.append(i)
                break
            ec_sum += ec_g
        else:
            raise ValueError("Maximum limit reached.")
    return plaintexts
