from __future__ import absolute_import, division, print_function, unicode_literals

from base64 import b64decode, b64encode as _b64encode

from django.utils.encoding import force_bytes, force_text

from petlib.bn import Bn
from petlib.ec import EcGroup, EcPt
from petlib.hmac import Hmac


def b64encode(*args, **kwargs):
    return force_text(_b64encode(*args, **kwargs))


def key_gen(t_num, nid=415):
    """
    Key generation, t_num is the number of trustees, nid is the curve ID. It
    returns a list of trustee keys and the public key of the election.
    """
    G = EcGroup(nid)
    ec_g = G.generator()
    order = G.order()
    bn_tk = []
    bn_sk = Bn(0)
    for i in range(t_num):
        bn_temp = order.random()
        bn_sk += bn_temp
        bn_tk.append(b64encode(bn_temp.binary()))
    ec_h = bn_sk * ec_g
    return bn_tk, b64encode(ec_h.export())


def ballot_gen(str_tk, str_h, bitmask, permutation, ballot_serial_number, part_tag, question_index, nid=415):
    """
    Ballot generation, str_tk is the list of trustee keys, str_h is the public
    key, bitmask is a binary array that indicates which options and blanks,
    permutation is the permutation array and nid is the curveID. It returns the
    ballot part.
    """
    G = EcGroup(nid)
    ec_g = G.generator()
    order = G.order()
    # read pk = h
    ec_h = EcPt.from_binary(b64decode(str_h), G)
    # read tk
    tk = []
    for k in str_tk:
        tk.append(b64decode(k))

    n = len(bitmask)
    assert n == len(permutation)

    # prefix sum for one bit
    total = 0  # the number of non-blank options
    for i in range(n):
        total += bitmask[i]
        bitmask[i] = (i + 1) * bitmask[i]

    # create vector encryptions
    rows = []  # n rows
    zk = []  # only for sum of b_i = 1 ZK, one row
    rand = []  # not published, only used for zk later

    for p, i in enumerate(permutation):  # i is the real index, p is the permuted index
        # the encryptions inside each row consist of c1,c2 and zks
        row_commitment = []
        row_zk = []  # last one is the 0/1 zk for each row
        row_r = []  # store r
        ctr = 0
        for j in range(n):
            if bitmask[j] == 0:
                continue

            # r_{i,j} = \Sum hmac_sk{ballot_serial_number, part_tag, question_index, b"rand", p, ctr}
            bn_r = Bn(0)
            for k in tk:
                h = Hmac(b"sha256", k)
                h.update(b",".join(
                    force_bytes(v) for v in [ballot_serial_number, part_tag, question_index, b"rand", p, ctr]))
                bn_temp = Bn.from_binary(h.digest())
                bn_r = bn_r.mod_add(bn_temp, order)
            row_r.append(bn_r)

            # zk
            bn_t = order.random()
            bn_s = order.random()
            bn_y = order.random()
            # T = Enc(t,s) Y = Enc((1-b)t,y)
            ec_T1 = bn_s * ec_g
            ec_T2 = bn_t * ec_g + bn_s * ec_h
            ec_Y1 = bn_y * ec_g
            ec_Y2 = bn_y * ec_h
            if i + 1 != bitmask[j]:  # b_i,j = 0
                ec_Y2 += bn_t * ec_g

            # compute delta 1 - 6
            bn_delta = []
            for m in range(6):
                bn_delta.append(Bn(0))
            for k in tk:
                for m in range(6):
                    h = Hmac(b"sha256", k)
                    h.update(b",".join(
                        force_bytes(v) for v in [ballot_serial_number, part_tag, question_index, b"zk", p, ctr, m]))
                    bn_temp = Bn.from_binary(h.digest())
                    bn_delta[m] = bn_delta[m].mod_add(bn_temp, order)

            # compute phi
            phi1 = bn_delta[0]
            phi2 = bn_delta[1].mod_add(bn_t, order)
            phi3 = bn_delta[2].mod_add(bn_r, order)
            phi4 = bn_delta[3].mod_add(bn_s, order)
            phi5 = bn_delta[4]
            bn_temp = bn_y.mod_add(bn_r.mod_mul(bn_t, order), order)
            phi6 = bn_delta[5].mod_sub(bn_temp, order)

            # encrypt b=1 if j = i, otherwise encrypt b=0
            ec_c1 = bn_r * ec_g
            ec_c2 = bn_r * ec_h
            if i + 1 == bitmask[j]:  # fix c2, phi1 and phi5 if b = 1
                ec_c2 += ec_g
                phi1 = phi1.mod_add(Bn(1), order)
                phi5 = phi5.mod_sub(bn_r, order)

            row_commitment.append({
                'C1': b64encode(ec_c1.export()),
                'C2': b64encode(ec_c2.export()),
            })
            row_zk.append({
                'T1': b64encode(ec_T1.export()),
                'T2': b64encode(ec_T2.export()),
                'Y1': b64encode(ec_Y1.export()),
                'Y2': b64encode(ec_Y2.export()),
                'phi1': b64encode(phi1.binary()),
                'phi2': b64encode(phi2.binary()),
                'phi3': b64encode(phi3.binary()),
                'phi4': b64encode(phi4.binary()),
                'phi5': b64encode(phi5.binary()),
                'phi6': b64encode(phi6.binary()),
            })
            ctr += 1  # update ctr

        # compute row ZK
        bn_u = order.random()
        bn_v = order.random()
        bn_z = order.random()
        # U = Enc(u,v) Z = Enc((1-\sum b_i)u,z)
        ec_U1 = bn_v * ec_g
        ec_U2 = bn_u * ec_g + bn_v * ec_h
        ec_Z1 = bn_z * ec_g
        ec_Z2 = bn_z * ec_h

        # compute \sum r_i for each row
        bn_row_r = Bn(0)
        for r in row_r:
            bn_row_r = bn_row_r.mod_add(r, order)

        # delta 7 - 12
        bn_delta_row = []
        for m in range(6):
            bn_delta_row.append(Bn(0))
        for k in tk:
            for m in range(6):
                h = Hmac(b"sha256", k)
                h.update(b",".join(
                    force_bytes(v) for v in [ballot_serial_number, part_tag, question_index, b"zk_row", p, m]))
                bn_temp = Bn.from_binary(h.digest())
                bn_delta_row[m] = bn_delta_row[m].mod_add(bn_temp, order)

        # phi 7 - 12
        phi7 = bn_delta_row[0]
        phi8 = bn_delta_row[1].mod_add(bn_u, order)
        phi9 = bn_delta_row[2].mod_add(bn_row_r, order)
        phi10 = bn_delta_row[3].mod_add(bn_v, order)
        phi11 = bn_delta_row[4]
        bn_temp = bn_z.mod_add(bn_row_r.mod_mul(bn_u, order), order)
        phi12 = bn_delta_row[5].mod_sub(bn_temp, order)

        if bitmask[i] == 0:  # \sum b_i = 0, fake ballots
            ec_Z2 += bn_u * ec_g
            phi7 = phi7.mod_add(Bn(1), order)
            phi11 = phi11.mod_sub(bn_row_r, order)

        row_zk.append({
            'U1': b64encode(ec_U1.export()),
            'U2': b64encode(ec_U2.export()),
            'Z1': b64encode(ec_Z1.export()),
            'Z2': b64encode(ec_Z2.export()),
            'phi7': b64encode(phi7.binary()),
            'phi8': b64encode(phi8.binary()),
            'phi9': b64encode(phi9.binary()),
            'phi10': b64encode(phi10.binary()),
            'phi11': b64encode(phi11.binary()),
            'phi12': b64encode(phi12.binary()),
        })  # the last one which is row ZK

        rows.append((row_commitment, row_zk))
        rand.append(row_r)

    # column ZK
    for ia in range(total):
        bn_delta_col = []  # delta13, 14
        bn_col_r = Bn(0)
        for m in range(2):
            bn_delta_col.append(Bn(0))
        for k in tk:
            for m in range(2):
                h = Hmac(b"sha256", k)
                h.update(b",".join(
                    force_bytes(v) for v in [ballot_serial_number, part_tag, question_index, b"zk_col", ia, m]))
                bn_temp = Bn.from_binary(h.digest())
                bn_delta_col[m] = bn_delta_col[m].mod_add(bn_temp, order)

        # compute sum of column r
        for ib in range(n):
            bn_col_r = bn_col_r.mod_add(rand[ib][ia], order)

        bn_w = order.random()
        ec_W1 = bn_w * ec_g
        ec_W2 = bn_w * ec_h
        phi13 = bn_delta_col[0].mod_add(bn_col_r, order)
        phi14 = bn_delta_col[1].mod_add(bn_w, order)

        zk.append({
            'W1': b64encode(ec_W1.export()),
            'W2': b64encode(ec_W2.export()),
            'phi13': b64encode(phi13.binary()),
            'phi14': b64encode(phi14.binary()),
        })

    return {'rows': rows, 'zk': zk}
