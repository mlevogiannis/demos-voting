from __future__ import absolute_import, division, print_function, unicode_literals

from petlib.ec import EcGroup, EcPt
from petlib.bn import Bn
from petlib.hmac import Hmac
from binascii import hexlify, b2a_base64, a2b_base64


def Test(nid = 713):
    G = EcGroup(nid)
    ec_g = G.generator()
    order = G.order()
    bn_sk = order.random()
    ec_h = bn_sk * ec_g
    test = ec_h.export()
    print(test)
    print(ec_h)
    str_sk = bn_sk.binary()
    print(hexlify(str_sk))
    if Bn.from_binary(str_sk) == bn_sk:
        print("TT")

    if EcPt.from_binary(test, G) == ec_h:
        print("True")

    return test

########################################################################################
# Key generation, t_num is the number of trustees, nid is the curve ID (use 713 for now)
# It returns a list of trustee keys and curve ID and the public key of the election.
########################################################################################
def KeyGen(t_num = 1, nid = 713):
    G = EcGroup(nid)
    ec_g = G.generator()
    order = G.order()
    bn_tk = []
    bn_sk = Bn(0)
    for i in range(t_num):
        bn_temp = order.random()
        bn_sk += bn_temp
        bn_tk.append(b2a_base64(bn_temp.binary()))
    ec_h = bn_sk * ec_g
    return (bn_tk, b2a_base64(ec_h.export()), nid)



########################################################################################
# Ballot generation, str_tk is the list of trustee keys, str_h is the public key, sn is serial number
# n1 is the number of options, n2 is the number of blank options, perm_arrays is a list of two permutation
# arrays, nid is the curve ID.
# It returns the ballot.
########################################################################################
def BallotGen(str_tk, str_h, sn = b"1", n1 = 1, n2 = 1, perm_arrays = None,  nid = 713):
    G = EcGroup(nid)
    ec_g = G.generator()
    order = G.order()
    #read pk = h
    ec_h = EcPt.from_binary(a2b_base64(str_h), G)
    #read tk
    tk = []
    for k in str_tk:
        tk.append(a2b_base64(k))
    #create vector encryptions
    Ballot = [] #Ballot of both A B sides
    #side A/B
    for side, perm in zip([b'A',b'B'], perm_arrays):
        assert n1 + n2 == len(perm)
        Row_side = [] #n1+n2 rows for each side
        ZK_side = [] #only for sum of b_i = 1 ZK, one row
        Rand_side = []#Not published, only used for zk later
        #for i in range(n1+n2):  #none-shuffle version
        for i in perm: #shuffle version
            row = [] # inside row there are each Enc, which consists of c1,c2 and zks  #Last one is the 0/1 zk for each row
            row_r = [] #store r
            for j in range(n1):
                #r_{i,j} = \Sum hmac_sk{sn,side, b"rand", i,j}
                bn_r = Bn(0)
                for k in tk:
                    h = Hmac(b"sha256",k)
                    h.update(sn+side+b"rand"+bytes(i)+bytes(j))
                    bn_temp = Bn.from_binary(h.digest())
                    bn_r = bn_r.mod_add(bn_temp, order)
                row_r.append(bn_r)
                #zk
                bn_t = order.random()
                bn_s = order.random()
                bn_y = order.random()
                #T = Enc(t,s) Y = Enc((1-b)t,y)
                ec_T1 = bn_s * ec_g
                ec_T2 = bn_t * ec_g + bn_s * ec_h
                ec_Y1 = bn_y * ec_g
                ec_Y2 = bn_y * ec_h
                if i != j:
                    ec_Y2 += bn_t * ec_g
                #compute delta 1 - 6
                bn_delta = []
                for m in range(6):
                    bn_delta.append(Bn(0))
                for k in tk:
                    for m in range(6):
                        h = Hmac(b"sha256",k)
                        h.update(sn+side+b"zk"+bytes(i)+bytes(j)+bytes(m))
                        bn_temp = Bn.from_binary(h.digest())
                        bn_delta[m] = bn_delta[m].mod_add(bn_temp, order)
                #compute phi
                phi1 = bn_delta[0]
                phi2 = bn_delta[1].mod_add(bn_t,order)
                phi3 = bn_delta[2].mod_add(bn_r,order)
                phi4 = bn_delta[3].mod_add(bn_s,order)
                phi5 = bn_delta[4]
                bn_temp = bn_y.mod_add(bn_r.mod_mul(bn_t,order),order)
                phi6 = bn_delta[5].mod_sub(bn_temp, order)
                #encrypt b=1 if j = i, otherwise encrypt b=0
                ec_c1 = bn_r * ec_g
                ec_c2 = bn_r * ec_h
                if i == j:#fix c2, phi1 and phi5 if b = 1
                    ec_c2 += ec_g
                    phi1 = phi1.mod_add(Bn(1),order)
                    phi5 = phi5.mod_sub(bn_r,order)
                row.append({'C1':b2a_base64(ec_c1.export()),'C2':b2a_base64(ec_c2.export()),'T1':b2a_base64(ec_T1.export()),'T2':b2a_base64(ec_T2.export()),'Y1':b2a_base64(ec_Y1.export()),'Y2':b2a_base64(ec_Y2.export()),'phi1':b2a_base64(phi1.binary()),'phi2':b2a_base64(phi2.binary()),'phi3':b2a_base64(phi3.binary()),'phi4':b2a_base64(phi4.binary()),'phi5':b2a_base64(phi5.binary()),'phi6':b2a_base64(phi6.binary())})
            #compute row ZK
            bn_u = order.random()
            bn_v = order.random()
            bn_z = order.random()
            #U = Enc(u,v) Z = Enc((1-\sum b_i)u,z)
            ec_U1 = bn_v * ec_g
            ec_U2 = bn_u * ec_g + bn_v * ec_h
            ec_Z1 = bn_z * ec_g
            ec_Z2 = bn_z * ec_h
            #compute \sum r_i for each row
            bn_row_r = Bn(0)
            for r in row_r:
                bn_row_r = bn_row_r.mod_add(r,order)

            #delta 7 - 12
            bn_delta_row = []
            for m in range(6):
                bn_delta_row.append(Bn(0))
            for k in tk:
                for m in range(6):
                    h = Hmac(b"sha256",k)
                    h.update(sn+side+b"zk_row"+bytes(i)+bytes(m))
                    bn_temp = Bn.from_binary(h.digest())
                    bn_delta_row[m] = bn_delta_row[m].mod_add(bn_temp, order)


            #phi 7 - 12
            phi7 = bn_delta_row[0]
            phi8 = bn_delta_row[1].mod_add(bn_u,order)
            phi9 = bn_delta_row[2].mod_add(bn_row_r,order)
            phi10 = bn_delta_row[3].mod_add(bn_v,order)
            phi11 = bn_delta_row[4]
            bn_temp = bn_z.mod_add(bn_row_r.mod_mul(bn_u,order),order)
            phi12 = bn_delta_row[5].mod_sub(bn_temp, order)

            if i >= n1: #\sum b_i = 0  fake ballots
                ec_Z2 +=bn_u * ec_g
                phi7 = phi7.mod_add(Bn(1),order)
                phi11 = phi11.mod_sub(bn_row_r,order)

            row.append({'U1':b2a_base64(ec_U1.export()),'U2':b2a_base64(ec_U2.export()),'Z1':b2a_base64(ec_Z1.export()),'Z2':b2a_base64(ec_Z2.export()),'phi7':b2a_base64(phi7.binary()), 'phi8':b2a_base64(phi8.binary()),'phi9':b2a_base64(phi9.binary()),'phi10':b2a_base64(phi10.binary()),'phi11':b2a_base64(phi11.binary()),'phi12':b2a_base64(phi12.binary())}) #the last one which is row ZK
            Row_side.append(row)
            Rand_side.append(row_r)
        #column ZK       n1 columns
        for ia in range(n1):
            bn_delta_col = []#delta13, 14
            bn_col_r = Bn(0)
            for m in range(2):
                bn_delta_col.append(Bn(0))
            for k in tk:
                for m in range(2):
                    h = Hmac(b"sha256",k)
                    h.update(sn+side+b"zk_col"+bytes(ia)+bytes(m))
                    bn_temp = Bn.from_binary(h.digest())
                    bn_delta_col[m] = bn_delta_col[m].mod_add(bn_temp, order)
            #compute sum of column r
            for ib in range(n1+n2):
                bn_col_r = bn_col_r.mod_add(Rand_side[ib][ia],order)

            bn_w = order.random()
            ec_W1 = bn_w * ec_g
            ec_W2 = bn_w * ec_h
            phi13 = bn_delta_col[0].mod_add(bn_col_r,order)
            phi14 = bn_delta_col[1].mod_add(bn_w,order)
            ZK_side.append({'W1':b2a_base64(ec_W1.export()),'W2':b2a_base64(ec_W2.export()),'phi13':b2a_base64(phi13.binary()),'phi14':b2a_base64(phi14.binary())})
        Ballot.append({'Row':Row_side,'ZK':ZK_side})


    return Ballot


########################################################################################
# Add commitment, nid is the curve ID (use 713 for now) and a list of commitments in forms of (c1,c2)
# It returns the combined commitment.
########################################################################################
def AddCom(commitments = [], nid = 713):
    if len(commitments)==0:
        return 0
    G = EcGroup(nid)
    ec_s1 = G.infinite()
    ec_s2 = G.infinite()
    for (c1,c2) in commitments:
        ec_c1 = EcPt.from_binary(a2b_base64(c1), G)
        ec_c2 = EcPt.from_binary(a2b_base64(c2), G)
        ec_s1 += ec_c1
        ec_s2 += ec_s2

    return (b2a_base64(ec_s1.export()),b2a_base64(ec_s2.export()))



########################################################################################
# Add decommitment, nid is the curve ID (use 713 for now) and a list of decommitments in forms of Bn
# It returns the combined decommitment.
########################################################################################
def AddDecom(decoms = [], nid = 713):
    if len(decoms)==0:
        return 0
    G = EcGroup(nid)
    order = G.order()
    bn_sum = Bn(0)
    for d in decoms:
        bn_sum = bn_sum.mod_add(Bn.from_binary(a2b_base64(d)),order)

    return b2a_base64(bn_sum.binary())
