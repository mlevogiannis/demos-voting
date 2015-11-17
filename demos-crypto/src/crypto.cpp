#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <sstream>
#include <unistd.h>
#include <string>
#include <iostream>
#include <fstream>
#include <math.h>
#include <stdint.h>

#include "miracl/ecn.h"
#include "miracl/big.h"
#include "miracl/miracl.h"

#include "crypto.hpp"
#include "protobuf/crypto.pb.h"

using namespace std;

///////////////////////////////////////////////////////////////
//crypto
//////////////////////////////////////////////////////////////

/* NIST p-192, p-224, p-256, p-384, p-521 elliptic curve
 * [0]: p192 = 2^{192} - 2^{64} - 1
 * [1]: p224 = 2^{224} - 2^{96} + 1
 * [2]: p256 = 2^{256} - 2^{224} + 2^{192} + 2^{96} - 1
 * [3]: p384 = 2^{384} - 2^{128} - 2^{96} + 2^{32} - 1
 * [4]: p521 = 2^{521} - 1
 */
/* elliptic curve prime */
const string ecp[] = {
    "fffffffffffffffffffffffffffffffeffffffffffffffff", // p192
    "ffffffffffffffffffffffffffffffff000000000000000000000001", //p224
    "ffffffff00000001000000000000000000000000ffffffffffffffffffffffff",//p256
    "fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffeffffffff0000000000000000ffffffff",//p384
    "000001FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"//p521
    };
    
/*Group order */
const string ecq[] = {
    "ffffffffffffffffffffffff99def836146bc9b1b4d22831", // p192
    "ffffffffffffffffffffffffffff16a2e0b8f03e13dd29455c5c2a3d", //p224
    "ffffffff00000000ffffffffffffffffbce6faada7179e84f3b9cac2fc632551",//p256
    "ffffffffffffffffffffffffffffffffffffffffffffffffc7634d81f4372ddf581a0db248b0a77aecec196accc52973",//p384
    "000001fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffa51868783bf2f966b7fcc0148f709a5d03bb5c9b8899c47aebb6fb71e91386409"//p521
    };

    

/* elliptic curve parameter A */
const string eca[] = {
    "fffffffffffffffffffffffffffffffefffffffffffffffc",//p192
    "fffffffffffffffffffffffffffffffefffffffffffffffffffffffe",//p224
    "ffffffff00000001000000000000000000000000fffffffffffffffffffffffc",//p256
    "fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffeffffffff0000000000000000fffffffc",//p384
    "000001FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFC"//p521
    };

/* elliptic curve parameter B */
const string ecb[] = {
    "64210519e59c80e70fa7e9ab72243049feb8deecc146b9b1",//p192
    "b4050a850c04b3abf54132565044b0b7d7bfd8ba270b39432355ffb4",//p224
    "5ac635d8aa3a93e7b3ebbd55769886bc651d06b0cc53b0f63bce3c3e27d2604b",//p256
    "b3312fa7e23ee7e4988e056be3f82d19181d9c6efe8141120314088f5013875ac656398d8a2ed19d2a85c8edd3ec2aef",//p384
    "00000051953eb9618e1c9a1f929a21a0b68540eea2da725b99b315f3b8b489918ef109e156193951ec7e937b1652c0bd3bb1bf073573df883d2c34f1ef451fd46b503f00"//p521
    };

/* elliptic curve - point of prime order (x,y) */
const string ecx[] = {
    "188da80eb03090f67cbf20eb43a18800f4ff0afd82ff1012",//p192
    "b70e0cbd6bb4bf7f321390b94a03c1d356c21122343280d6115c1d21",//p244
    "6b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c296",//p256
    "aa87ca22be8b05378eb1c71ef320ad746e1d3b628ba79b9859f741e082542a385502f25dbf55296c3a545e3872760aB7",//p384
    "000000c6858e06b70404e9cd9e3ecb662395b4429c648139053fb521f828af606b4d3dbaa14b5e77efe75928fe1dc127a2ffa8de3348b3c1856a429bf97e7e31c2e5bd66"//p521
    };

const string ecy[] = {
    "07192b95ffc8da78631011ed6b24cdd573f977a11e794811",//p192
    "bd376388b5f723fb4c22dfe6cd4375a05a07476444d5819985007e34",//p224
    "4fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5",//p256
    "3617de4a96262c6f5d9e98bf9292dc29f8f41dbd289a147ce9da3113b5f0b8c00a60b1ce1d7e819d7a431d7c90ea0e5F",//p384
    "0000011839296a789a3bc0045c8a5fb42c7d1bd998f54449579b446817afbd17273e662c97ee72995ef42640c550b9013fad0761353c7086a272c24088be94769fd16650"//p521
    };

/*Randomness bits*/
const int RandLen[] ={191,223,255,383,520};



//Key Generation
void KeyGen(const CryptoRequest_KeyGenData& data, Key* key)
{
    #ifndef MR_NOFULLWIDTH
    Miracl precision(50,0);
    #else
    Miracl precision(50,MAXBASE);
    #endif
    
    int curve = data.curve();
    unsigned long randseed;
    char c[128];
    Big sk,a,b,p,x,y;
    ECn g,h;
    miracl *mip=&precision;
    
    //random seed
    ifstream f("/dev/urandom");
    f.read(reinterpret_cast<char*>(&randseed), sizeof(randseed));
    irand(randseed);
    a=-3;
    mip->IOBASE=16;
    b=(char *)(ecb[curve].c_str());
    p=(char *)(ecp[curve].c_str());
    ecurve(a,b,p,MR_BEST);  // means use PROJECTIVE if possible, else AFFINE coordinates
    x=(char *)(ecx[curve].c_str());
    y=(char *)(ecy[curve].c_str());
    g=ECn(x,y);
    //Generate and output pk and sk
    key->set_curve(curve);
    sk=rand(RandLen[curve],2);
    mip->IOBASE=64;
    c<<sk;
    key->set_sk(string(c));
    h = sk*g;
    GG *pk = key->mutable_pk();
    h.get(x,y);
    c<<x;
    pk->set_x(string(c));
    c<<y;
    pk->set_y(string(c));
}


//Generate Ballots
void GenBallot(const CryptoRequest_GenBallotData& data, CryptoResponse_BallotData* ballot_data, unsigned int copies)
{        
    #ifndef MR_NOFULLWIDTH
    Miracl precision(50,0);
    #else
    Miracl precision(50,MAXBASE);
    #endif    
    
    const Key& key = data.key();
    int curve = key.curve();
    int NumOpt = data.options();
    int NumBlk = data.blanks();
    unsigned long randseed;
    char c[128];
    Big r,a,b,p,q,x,y;
    ECn g,h, c1,c2;
    miracl *mip=&precision;
    //random seed
    ifstream f("/dev/urandom");
    f.read(reinterpret_cast<char*>(&randseed), sizeof(randseed));
    irand(randseed);
    //Read g
    a=-3;
    mip->IOBASE=16;
    q=(char *)(ecq[curve].c_str());    
    b= (char *)(ecb[curve].c_str());
    p=(char *)(ecp[curve].c_str());
    ecurve(a,b,p,MR_BEST);  // means use PROJECTIVE if possible, else AFFINE coordinates
    x=(char *)(ecx[curve].c_str());
    y=(char *)(ecy[curve].c_str());
    g=ECn(x,y);
    //Read PK
    mip->IOBASE=64;
    x = (char *)key.pk().x().c_str();
    y = (char *)key.pk().y().c_str();
    h = ECn(x,y);    
    
    //generate ballots
    for(unsigned int i = 0; i < copies; i++){
        //options
        CryptoResponse_BallotData_Ballot *eachB = ballot_data->add_ballot();
        for(unsigned int j = 1; j <= NumOpt; j++){
            //a unit vector
            CryptoResponse_BallotData_Ballot_Enc *opt = eachB->add_opt();
            Com *com = opt->mutable_com();
            ZK1 *zk1 = opt->mutable_zk1();
            ZKState *state = opt->mutable_zk_state();
            Decom *decom = opt->mutable_decom();
            //debug
            //cout<<"j = " <<j<<endl;
            for(int ctr = 1; ctr <= NumOpt ; ctr++){
                r = rand(RandLen[curve],2);    
                c1 = r*g;
                c2 = r*h;
                Decom_Dpair *pair = decom->add_dp();
                c<<r;
                pair->set_randomness(string(c));
                if(ctr == j){
                    c2+=g;  //Enc of 1
                    pair->set_msg(1);
                    //debug
                    //cout<<"1"<<endl;
                }
                else{
                    pair->set_msg(0);
                }
                    GG *G = com->add_element();
                c1.get(x,y);
                c<<x;
                G->set_x(string(c));
                c<<y;
                G->set_y(string(c));
                //debug
                //cout<<x<<endl<<y<<endl;
            }
        }
        
        //blanks
        for(unsigned int j = 0; j < NumBlk; j++){
             //a zero vector
            CryptoResponse_BallotData_Ballot_Enc *opt = eachB->add_blank();
            Com *com = opt->mutable_com();
            ZK1 *zk1 = opt->mutable_zk1();
            ZKState *state = opt->mutable_zk_state();
            Decom *decom = opt->mutable_decom();
            //debug
            //cout<<"j = " <<j<<endl;
            for(int ctr = 1; ctr <= NumOpt ; ctr++){
                r = rand(RandLen[curve],2);
                c1 = r*g;
                c2 = r*h;
                Decom_Dpair *pair = decom->add_dp();
                c<<r;
                pair->set_randomness(string(c));
                pair->set_msg(0);
                GG *G = com->add_element();
                c1.get(x,y);
                c<<x;
                G->set_x(string(c));
                c<<y;
                G->set_y(string(c));
                //debug
                //cout<<x<<endl<<y<<endl;
            }
        }
    }
}


// Add Ballots
void AddCom(const CryptoRequest_AddComData& data, Com* combined_com)
{
    #ifndef MR_NOFULLWIDTH
    Miracl precision(50,0);
    #else
    Miracl precision(50,MAXBASE);
    #endif
    
    const Key& key = data.key();
    int curve = key.curve();
    char c[128];
    Big r,a,b,p,q,x,y;
    ECn g,h, c1,c2;
    miracl *mip=&precision;
    //Read g
    a=-3;
    mip->IOBASE=16;
    q=(char *)(ecq[curve].c_str());
    b= (char *)(ecb[curve].c_str());
    p=(char *)(ecp[curve].c_str());
    ecurve(a,b,p,MR_BEST);  // means use PROJECTIVE if possible, else AFFINE coordinates
    x=(char *)(ecx[curve].c_str());
    y=(char *)(ecy[curve].c_str());
    g=ECn(x,y);
    //Read PK
    mip->IOBASE=64;
    x = (char *)key.pk().x().c_str();
    y = (char *)key.pk().y().c_str();
    h = ECn(x,y);
    
    ECn *sum;
    int length = 0;
    //add com
    for(int i = 0 ; i < data.com_size() ; i++){
        const Com& each = data.com(i);
        //if the first loop, set sum_com
        if(i==0){
            length = each.element_size();
            sum = new ECn[length];
        }
        for(int j = 0 ; j < length ; j++){
            const GG& G = each.element(j);
            x = (char *)G.x().c_str();
            y = (char *)G.y().c_str();
            c1 = ECn(x,y);
            if(i==0){
                sum[j] = c1;
            }
            else{
                sum[j]+=c1;
            }
        }
    }
    
    //output
    for(int j = 0; j< length; j++){
        GG *G = combined_com->add_element();
        sum[j].get(x,y);
        c<<x;
        G->set_x(string(c));
        c<<y;
        G->set_y(string(c));
        //cout<<"x = "<<x<<endl<<"y = "<<y<<endl;
    }
}


// Add decommitment
void AddDecom(const CryptoRequest_AddDecomData& data, Decom* combined_decom)
{
    #ifndef MR_NOFULLWIDTH
    Miracl precision(50,0);
    #else
    Miracl precision(50,MAXBASE);
    #endif
    
    const Key& key = data.key();
    int curve = key.curve();
    int message = 0;
    char c[128];
    Big a,b,p,q,x,y;
    ECn g,h, c1,c2;
    miracl *mip=&precision;
    
    //Read g
    a=-3;
    mip->IOBASE=16;
    q=(char *)(ecq[curve].c_str());
    b= (char *)(ecb[curve].c_str());
    p=(char *)(ecp[curve].c_str());
    ecurve(a,b,p,MR_BEST);  // means use PROJECTIVE if possible, else AFFINE coordinates
    x=(char *)(ecx[curve].c_str());
    y=(char *)(ecy[curve].c_str());
    g=ECn(x,y);
    //Read PK
    mip->IOBASE=64;
    x = (char *)key.pk().x().c_str();
    y = (char *)key.pk().y().c_str();
    h = ECn(x,y);
    
    //add decom
    
    Big *sum;
    int *msg_vec;
    int length = 0;
    //add com
    for(int i = 0 ; i < data.decom_size() ; i++){
        const Decom& each = data.decom(i);
        //if the first loop, set sum_com
        if(i==0){
            length = each.dp_size();
            sum = new Big[length];
            msg_vec = new int[length];
        }
        for(int j = 0 ; j < length ; j++){
            const Decom_Dpair& pair = each.dp(j);
            x = (char *)pair.randomness().c_str();
            message = pair.msg();
            if(i==0){
                sum[j] = x;
                msg_vec[j] = message;
            }
            else{
                 sum[j]+=x;
                msg_vec[j]+=message;
            }
            
            //cout<<"i = "<<i<<"j = "<<j<<"   "<<msg_vec[j]<<endl;
        }
    }
    
    //output
    for(int j = 0; j< length; j++){
        
        Decom_Dpair *dep = combined_decom->add_dp();
        c<<sum[j];
        dep->set_randomness(string(c));
        dep->set_msg(msg_vec[j]);
    }
}


// Complete ZK
void CompleteZK(const CryptoRequest_CompleteZKData& data, CryptoResponse_ZKSet* zk_set)
{
    for(int i = 0; i< data.zk_set_size();i++){
        zk_set->add_zk2();
    }
}


// Verify commitment - decommitment
bool VerifyCom(const CryptoRequest_VerifyComData& data)
{
    return true;
}

