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
		
	    int curve = 0;
		unsigned long randseed;
		char c[100];
		Big sk,a,b,p,x,y;
		ECn g,h;
		miracl *mip=&precision;
		
		//cout << "KeyGen  N = " << data.ballots() <<"  m = "<< data.options() << endl;
		//determine the curve NB: insecure, length may be out of bound
		double maxlen = data.options() * log2(1.0+data.ballots());
		//cout<<"Max length: "<< maxlen<<endl;
		if(maxlen < 191) curve = 0;
		else if (maxlen < 223) curve = 1;
		else if (maxlen < 255) curve = 2;
		else if (maxlen < 383) curve = 3;
		else curve = 4;
		
		//random seed 
		ifstream f("/dev/urandom"); 
		f.read(reinterpret_cast<char*>(&randseed), sizeof(randseed)); 
		irand(randseed);
		a=-3;
		mip->IOBASE=16;
		b= (char *)(ecb[curve].c_str());
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
		if(h.get(x) == 1) pk->set_y(true);
		else pk->set_y(false);//<x,y> is compressed form of public key
		c<<x;
		pk->set_x(string(c));
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
		
	    int iy,logm, curve = key.curve();
		unsigned long randseed;
		char c[100];
		Big tempB,a,b,p,q,x,y,r,temp1,temp2,temp3,temp4,Num = data.ballots()+1;
		ECn g,h,c1,c2,tempE;
		miracl *mip=&precision;
		
		/////////////////////////////////
		//ZK stuff
		//compute log m
		logm = (int) (log2(data.options()) + 0.9999);
		int ZKb[logm];		
		Big ZKt[logm], ZKz[logm],ZKy[logm],ZKr[logm],ZKw[logm],ZKf[logm],ZKa[logm],ZKrp[logm],ZKbeta[logm+1],ZKgamma[logm+1];	
		ECn ZKB1[logm],ZKY1[logm],ZKT1[logm],ZKW1[logm],ZKB2[logm],ZKY2[logm],ZKT2[logm],ZKW2[logm], ZKD1[logm],ZKD2[logm];	
		////////////////////////////////
		
		//cout << "GenBallot  N = " << data.ballots() <<"  m = "<< options <<"  Number of copies:  "<<copies<< endl;
		//cout<< "PK: "<<key.pk().x()<<" "<<key.pk().y()<<endl;
		//cout<<"Curve: "<<curve<<endl;
		
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
		iy = key.pk().y();
		h = ECn(x,iy); //decompress pk
		
		//generate ballots
		for(unsigned int i = 0; i < copies; i++){
			CryptoResponse_BallotData_Ballot *eachB = ballot_data->add_ballot();
			for(unsigned int j = 0;j<data.options();j++){
				//each Enc
				CryptoResponse_BallotData_Ballot_Enc *enc = eachB->add_enc();
				//commitment
				tempB = pow(Num,j);
				//r=rand(RandLen[curve],2);
				//r is determined by ZK r_j
				r = 1;
				//ZK
				for (int ctr = 0; ctr<logm;ctr++){
						//random ZK elements
						ZKt[ctr] = rand(RandLen[curve],2);
						ZKz[ctr] = rand(RandLen[curve],2);
						ZKy[ctr] = rand(RandLen[curve],2);
						ZKr[ctr] = rand(RandLen[curve],2);
						ZKw[ctr] = rand(RandLen[curve],2);
						ZKf[ctr] = rand(RandLen[curve],2);
						ZKrp[ctr] = modmult(ZKr[ctr] , (pow(Num,pow(2,ctr))-1),q);// compute r'
						r = modmult(r, ZKrp[ctr] , q);//r = /prod r_j'
				}
				//write to Decom
				c<<r;
				Decom *decom = enc->mutable_decom();
				decom->set_randomness(string(c));
				c<<tempB;
				decom->set_msg(string(c));
				//write com
				Com *com = enc->mutable_com();
				GG *G1 = com->mutable_c1();
				c1 = r*g;
				if(c1.get(x) == 1) G1->set_y(true);
				else G1->set_y(false);
				c<<x;
				G1->set_x(string(c));
				GG *G2 = com->mutable_c2();
				c2 = tempB*g;
				tempE = r*h;
				c2+=tempE; //avoid temp variables
				if(c2.get(x) == 1) G2->set_y(true);
				else G2->set_y(false);
				c<<x;
				G2->set_x(string(c));
				//write ZK

				//compute b_i  and a_j
				iy = j;//iy is used as temp int
				for (int ctr = 0; ctr<logm;ctr++){
						ZKb[ctr] = iy%2;
						iy = (iy - ZKb[ctr])/2;
						//a_j = N^{2^j} is b_j = 1 and  a_j = 1 if b_j = 0
						if(ZKb[ctr] == 1) ZKa[ctr] =  pow(Num,pow(2,ctr));
						else ZKa[ctr] = 1;
				}
				//committing B T Y W
				for (int ctr = 0; ctr<logm;ctr++){
						ZKB1[ctr] = ZKr[ctr]*g;
						if(ZKb[ctr] == 1) {
							ZKB2[ctr] = g;
							ZKB2[ctr] += ZKr[ctr]*h;
						}
						else ZKB2[ctr] = ZKr[ctr]*h;
						
						ZKT1[ctr] = ZKz[ctr]*g;
						ZKT2[ctr] = ZKt[ctr]*g;
						tempE = ZKz[ctr]*h;
						ZKT2[ctr] += tempE;
						
						ZKY1[ctr] = ZKy[ctr]*g;
						if(ZKb[ctr] == 0) {
							ZKY2[ctr] = ZKt[ctr]*g;
							tempE = ZKy[ctr]*h;
							ZKY2[ctr] += tempE;
						}	
						else ZKY2[ctr] = ZKy[ctr]*h;						

						ZKW1[ctr] = ZKf[ctr]*g;
						ZKW2[ctr] = ZKw[ctr]*g;
						tempE = ZKf[ctr]*h;
						ZKW2[ctr] += tempE;

				}				
				
				//compute beta and gamma 
				for (int ctr = 0; ctr<logm;ctr++){
						if(ctr == 0){
								ZKbeta[1] = ZKa[0];
								ZKbeta[0] = ZKw[0];
								ZKgamma[1] = ZKrp[0];
								ZKgamma[0] = ZKf[0];								
								continue;
						}
						temp1 = ZKbeta[0];//it will be overwriteen
						temp2 = ZKgamma[0];//it will be overwriteen
						ZKbeta[ctr+1] = modmult(ZKa[ctr] , ZKbeta[ctr],q);
						ZKbeta[0] = modmult(ZKbeta[0], ZKw[ctr],q); 
						ZKgamma[ctr+1] = modmult(ZKrp[ctr] , ZKgamma[ctr],q);
						ZKgamma[0] = modmult(ZKgamma[0], ZKf[ctr],q); 						
						for(int k = 1 ; k<= ctr ; k++){
								temp3 = ZKbeta[k]; //copy before write
								temp4 = ZKgamma[k];//copy before write
								ZKbeta[k] = modmult(ZKbeta[k] , ZKw[ctr],q) + modmult(temp1 , ZKa[ctr],q);
								ZKgamma[k] = modmult(ZKgamma[k] , ZKf[ctr],q) + modmult(temp2 , ZKrp[ctr],q);
								temp1 = temp3;//beta k
								temp2 = temp4;//gamma k								
						}
				}	
				//compute D_j and write B T Y W D
				ZK1 *zk1 = enc->mutable_zk1();	
				GG *element;	
			/////////////////////////////////////////////
			/*			
				//write statement E com for verification test
				//E1
				zk1->add_element()->CopyFrom(enc->com().c1());
				//E2
				zk1->add_element()->CopyFrom(enc->com().c2());					
			*/
			/////////////////////////////////////////////				
				for (int ctr = 0; ctr<logm;ctr++){
						ZKD1[ctr] = ZKgamma[ctr]*g;
						ZKD2[ctr] = ZKbeta[ctr]*g;
						tempE = ZKgamma[ctr]*h;
						ZKD2[ctr] += tempE;
						//write ZK1
						//B1
						element = zk1->add_element();
						if(ZKB1[ctr].get(x) == 1) element->set_y(true);
						else element->set_y(false);
						c<<x;
						element->set_x(string(c));
						//B2
						element = zk1->add_element();
						if(ZKB2[ctr].get(x) == 1) element->set_y(true);
						else element->set_y(false);
						c<<x;
						element->set_x(string(c));
						//T1
						element = zk1->add_element();
						if(ZKT1[ctr].get(x) == 1) element->set_y(true);
						else element->set_y(false);
						c<<x;
						element->set_x(string(c));
						//T2
						element = zk1->add_element();
						if(ZKT2[ctr].get(x) == 1) element->set_y(true);
						else element->set_y(false);
						c<<x;
						element->set_x(string(c));
						//Y1
						element = zk1->add_element();
						if(ZKY1[ctr].get(x) == 1) element->set_y(true);
						else element->set_y(false);
						c<<x;
						element->set_x(string(c));
						//Y2
						element = zk1->add_element();
						if(ZKY2[ctr].get(x) == 1) element->set_y(true);
						else element->set_y(false);
						c<<x;
						element->set_x(string(c));	
						//W1
						element = zk1->add_element();
						if(ZKW1[ctr].get(x) == 1) element->set_y(true);
						else element->set_y(false);
						c<<x;
						element->set_x(string(c));
						//W2
						element = zk1->add_element();
						if(ZKW2[ctr].get(x) == 1) element->set_y(true);
						else element->set_y(false);
						c<<x;
						element->set_x(string(c));
						//D1
						element = zk1->add_element();
						if(ZKD1[ctr].get(x) == 1) element->set_y(true);
						else element->set_y(false);
						c<<x;
						element->set_x(string(c));
						//D2
						element = zk1->add_element();
						if(ZKD2[ctr].get(x) == 1) element->set_y(true);
						else element->set_y(false);
						c<<x;
						element->set_x(string(c));																	
				}				
				
				//write ZK state t z y r b w f [a, rp]
				ZKState *zk_state = enc->mutable_zk_state();
				for (int ctr = 0; ctr<logm;ctr++){
						//t
						tempB = ZKt[ctr];
						c<< tempB;
						zk_state->add_zp(string(c));
						//z
						tempB = ZKz[ctr];
						c<<tempB;
						zk_state->add_zp(string(c));
						//y
						tempB = ZKy[ctr];
						c<<tempB;
						zk_state->add_zp(string(c));
						//r
						tempB = ZKr[ctr];
						c<<tempB;
						zk_state->add_zp(string(c));
						//b  b is special
						if(ZKb[ctr] == 1) zk_state->add_zp("1");
						else zk_state->add_zp("0");
						//w
						tempB = ZKw[ctr];
						c<<tempB;
						zk_state->add_zp(string(c));	
						//f
						tempB = ZKf[ctr];
						c<<tempB;
						zk_state->add_zp(string(c));		
						//a
						tempB = ZKa[ctr];
						c<<tempB;
						zk_state->add_zp(string(c));	
						//rp
						tempB = ZKrp[ctr];
						c<<tempB;
						zk_state->add_zp(string(c));																					
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
	    int iy,curve = key.curve();
		char c[100];
		Big a,b,p,x,y;
		ECn c1,c2,s1,s2;
		miracl *mip=&precision;
		//read curve param
		a=-3;
		mip->IOBASE=16;
		b= (char *)(ecb[curve].c_str());
		p=(char *)(ecp[curve].c_str());
		ecurve(a,b,p,MR_BEST);  // means use PROJECTIVE if possible, else AFFINE coordinates
		mip->IOBASE=64;
		
		//cout<<"Add commitments:"<<endl;
		//cout<< "PK: "<<key.pk().x()<<" "<<key.pk().y()<<endl;
		//cout<<"Curve: "<<curve<<endl;
		
		//Add commitments
		for(int i = 0; i < data.com_size(); i++){
			const Com& com = data.com(i);
			x = (char *)com.c1().x().c_str();
			iy = com.c1().y();
			c1 = ECn(x,iy); //decompress
			x = (char *)com.c2().x().c_str();
			iy = com.c2().y();
			c2 = ECn(x,iy); //decompress			
			if(i==0){
				s1 = c1;
				s2 = c2;
			}
			else{
				s1 += c1;
				s2 += c2;
			}
			
		}

		//write com
		GG *G1 = combined_com->mutable_c1();
		if(s1.get(x) == 1) G1->set_y(true);
		else G1->set_y(false);
		c<<x;
		G1->set_x(string(c));
		GG *G2 = combined_com->mutable_c2();
		if(s2.get(x) == 1) G2->set_y(true);
		else G2->set_y(false);
		c<<x;
		G2->set_x(string(c)); 
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
		char c[100];
		Big a,b,q,x,y,s1,s2;
		miracl *mip=&precision;
		
		//cout<<"Add decommitments:"<<endl;
		//cout<< "PK: "<<key.pk().x()<<" "<<key.pk().y()<<endl;
		//cout<<"Curve: "<<curve<<endl;
		//only need q
		mip->IOBASE=16;
		q=(char *)(ecq[curve].c_str());	
		mip->IOBASE=64;	
		//Add decommitments
		for(int i = 0; i < data.decom_size(); i++){
			const Decom& decom = data.decom(i);
			x = (char *)decom.msg().c_str();
			y = (char *)decom.randomness().c_str();
			if(i==0){
				s1 = x;
				s2 = y;
			}
			else{
				s1 += x;
				s2 += y;
			}
			
		}
		
		// a stupid way to mod q
		x = 1;
		s1 = modmult(s1,x,q);
		s2 = modmult(s2,x,q);
		mip->IOBASE=64;
		c<<s1;
		combined_decom->set_msg(c);
		c<<s2;
		combined_decom->set_randomness(c);
}


// Complete ZK
void CompleteZK(const CryptoRequest_CompleteZKData& data, CryptoResponse_ZKSet* zk_set)
{
		#ifndef MR_NOFULLWIDTH
		Miracl precision(50,0);
		#else 
		Miracl precision(50,MAXBASE);
		#endif
		
		const Key& key = data.key();
	    int iy,k,logm,curve = key.curve();
		char c[100];//,hash[32];
		//char *coins;
		Big tempB,a,b,p,q,x,y,r,s1,s2,ch;
		ECn g,h,c1,c2,tempE;
		miracl *mip=&precision;
		/////////////////////////////////
		//ZK stuff
		//compute log m
		logm = (int) (log2(data.options()) + 0.9999);
		int ZKb[logm];		
		Big ZKt[logm], ZKz[logm],ZKy[logm],ZKr[logm],ZKw[logm],ZKf[logm],ZKa[logm],ZKrp[logm];
		Big ZKtp[logm],	ZKzp[logm],ZKyp[logm],ZKwp[logm],ZKfp[logm];	
		/*
		ECn ZKB1[logm],ZKY1[logm],ZKT1[logm],ZKW1[logm],ZKB2[logm],ZKY2[logm],ZKT2[logm],ZKW2[logm], ZKD1[logm],ZKD2[logm];//only for verification
		*/
		////////////////////////////////
		//cout<<"Complete ZK:"<<endl;
		//cout<< "PK: "<<key.pk().x()<<" "<<key.pk().y()<<endl;
		//cout<<"Curve: " << curve << endl;
		//cout<<"log m: " << logm << endl;
		//cout<<"coins: " << coins<<endl;
		mip->IOBASE=16;
		//only take the first 27 bytes for now to fit p224
		string coins(data.coins(), 2*27);
		ch = (char *)coins.c_str();
		//Read g
		a=-3;
		q=(char *)(ecq[curve].c_str());	
		b= (char *)(ecb[curve].c_str());
		p=(char *)(ecp[curve].c_str());
		ecurve(a,b,p,MR_BEST);  // means use PROJECTIVE if possible, else AFFINE coordinates
		x=(char *)(ecx[curve].c_str());
		y=(char *)(ecy[curve].c_str());
		g=ECn(x,y);
		//Read PK = h
		mip->IOBASE=64;
		x = (char *)key.pk().x().c_str();
		iy = key.pk().y();
		h = ECn(x,iy); //decompress pk
		
		//finish ZK
		for(int i = 0; i< data.zk_set_size();i++){
				const CryptoRequest_CompleteZKData_ZKSet& zkset = data.zk_set(i);
				/////////////////////////////////////
				/*
				//read ZK1 in order  B T Y W D
				//In fact no need ZK1!!!!! Only read for verification
				
				const ZK1& zk1 = zkset.zk1();
				k = 0;	   
				//////////////////////////////////////////////////
				//read com E statement for verification test only
				ECn ZKtemp1,ZKtemp2,ZKtemp3,prodD1,prodD2,E1,E2;
				Big prodw,prodf;
				x = (char *) zk1.element(k).x().c_str();
				iy = zk1.element(k).y();	
				E1 = ECn(x,iy);
				k++;
				x = (char *) zk1.element(k).x().c_str();
				iy = zk1.element(k).y();	
				E2 = ECn(x,iy);
				k++;
				//////////////////////////////////////////////////
				for (int ctr = 0; ctr<logm;ctr++){
						if(k >= zk1.element_size()) break;//in case out of bound
				
						//B1
						x = (char *) zk1.element(k).x().c_str();
						iy = zk1.element(k).y();	
						ZKB1[ctr] = ECn(x,iy);
						k++;
						//B2
						x = (char *) zk1.element(k).x().c_str();
						iy = zk1.element(k).y();	
						ZKB2[ctr] = ECn(x,iy);
						k++;
						//T1
						x = (char *) zk1.element(k).x().c_str();
						iy = zk1.element(k).y();	
						ZKT1[ctr] = ECn(x,iy);
						k++;
						//T2
						x = (char *) zk1.element(k).x().c_str();
						iy = zk1.element(k).y();	
						ZKT2[ctr] = ECn(x,iy);
						k++;
						//Y1
						x = (char *) zk1.element(k).x().c_str();
						iy = zk1.element(k).y();	
						ZKY1[ctr] = ECn(x,iy);
						k++;
						//Y2
						x = (char *) zk1.element(k).x().c_str();
						iy = zk1.element(k).y();	
						ZKY2[ctr] = ECn(x,iy);
						k++;
						//W1
						x = (char *) zk1.element(k).x().c_str();
						iy = zk1.element(k).y();	
						ZKW1[ctr] = ECn(x,iy);
						k++;
						//W2
						x = (char *) zk1.element(k).x().c_str();
						iy = zk1.element(k).y();	
						ZKW2[ctr] = ECn(x,iy);
						k++;
						//D1
						x = (char *) zk1.element(k).x().c_str();
						iy = zk1.element(k).y();	
						ZKD1[ctr] = ECn(x,iy);
						k++;
						//D2
						x = (char *) zk1.element(k).x().c_str();
						iy = zk1.element(k).y();	
						ZKD2[ctr] = ECn(x,iy);
						k++;
						
				}
				*/
				////////////////////////////////////////////////////////////
				
				//read ZK state  t z y r b w f [a, rp]
				const ZKState& zk_state = zkset.zk_state();
				k = 0;		
				for (int ctr = 0; ctr<logm;ctr++){
						if(k >= zk_state.zp_size()) break;//in case out of bound
						//t
						ZKt[ctr] = (char *)zk_state.zp(k).c_str();
						k++;
						//z
						ZKz[ctr] = (char *)zk_state.zp(k).c_str();
						k++;
						//y
						ZKy[ctr] = (char *)zk_state.zp(k).c_str();
						k++;
						//r
						ZKr[ctr] = (char *)zk_state.zp(k).c_str();
						k++;
						//b  b is special
						if(zk_state.zp(k).compare("1") == 0)ZKb[ctr] = 1;
						else ZKb[ctr] = 0;
						k++;
						//w
						ZKw[ctr] = (char *)zk_state.zp(k).c_str();
						k++;	
						//f
						ZKf[ctr] = (char *)zk_state.zp(k).c_str();
						k++;		
						//a
						ZKa[ctr] = (char *)zk_state.zp(k).c_str();
						k++;
						//rp
						ZKrp[ctr] = (char *)zk_state.zp(k).c_str();
						k++;	
						
						//complete ZK2
						//t'
						if (ZKb[ctr] == 0) ZKtp[ctr] = ZKt[ctr];
						else ZKtp[ctr] = ch + ZKt[ctr];
						//z'
						ZKzp[ctr] = modmult(ZKr[ctr],ch,q) + ZKz[ctr];
						//y'
						ZKyp[ctr] = 0 - ZKy[ctr] - modmult(ZKr[ctr],ZKtp[ctr],q);
						//w'
						ZKwp[ctr] = modmult(ZKa[ctr],ch,q) + ZKw[ctr];
						//f'
						ZKfp[ctr] = modmult(ZKrp[ctr],ch,q) + ZKf[ctr];
																								
				}
				
				//write ZK2   t'  z'  y'  w'  f'
				ZK2 *eachzk2 = zk_set->add_zk2();
				for (int ctr = 0; ctr<logm;ctr++){
						//t
						tempB = ZKtp[ctr];
						c<< tempB;
						eachzk2->add_zp(string(c));
						//z'
						tempB = ZKzp[ctr];
						c<<tempB;
						eachzk2->add_zp(string(c));
						//y'
						tempB = ZKyp[ctr];
						c<<tempB;
						eachzk2->add_zp(string(c));
						//w'
						tempB = ZKwp[ctr];
						c<<tempB;
						eachzk2->add_zp(string(c));
						//f'
						tempB = ZKfp[ctr];
						c<<tempB;
						eachzk2->add_zp(string(c));																		
				}	
				
				//////////////////////////////////////////////////////
				//test ZK verification
	/*
				for (int ctr = 0; ctr<logm;ctr++){
					//check equation ch*B + T = com(t';z')
						ZKtemp1 = ch*ZKB1[ctr];
						ZKtemp2 = ZKT1[ctr];
						ZKtemp1 += ZKtemp2;
						if(ZKtemp1 == ZKzp[ctr]*g )//cout<<"================Verified (1)!! "<<ctr<<endl;
						else //cout<<"================NOT NOT NOT Verified (1)!! "<<ctr<<endl;
						ZKtemp1 = ch*ZKB2[ctr];
						ZKtemp2 = ZKT2[ctr];
						ZKtemp1 += ZKtemp2;
						ZKtemp3 = ZKtp[ctr] * g;
						ZKtemp2 = ZKzp[ctr] * h;
						ZKtemp3 +=ZKtemp2;
						if(ZKtemp1 == ZKtemp3 )//cout<<"================Verified (2)!!"<<endl;
						else //cout<<"================NOT NOT NOT Verified (2)!!"<<endl;
					//check equation (com(1;0)/B)^t' / Y = com(0;y')
						ZKtemp2 = 0 * g;
						ZKtemp2 -= ZKB1[ctr];
						ZKtemp1 = ZKtp[ctr] * ZKtemp2;
						ZKtemp1 -= ZKY1[ctr];
						if(ZKtemp1 == ZKyp[ctr]*g )//cout<<"================Verified (3)!!"<<endl;
						else //cout<<"================NOT NOT NOT Verified (3)!!"<<endl;
						ZKtemp2 = g;
						ZKtemp2 -= ZKB2[ctr];
						ZKtemp1 = ZKtp[ctr] * ZKtemp2;
						ZKtemp1 -= ZKY2[ctr];
						if(ZKtemp1 == ZKyp[ctr]*h )//cout<<"================Verified (4)!!"<<endl;
						else //cout<<"================NOT NOT NOT Verified (4)!!"<<endl;
					//check equation A^ch + W = com(w';f')
						tempB = 601;
						tempB = pow(tempB,pow(2,ctr))-1;
						ZKtemp1 = tempB * ZKB1[ctr];//A
						ZKtemp1 *= ch;
						ZKtemp1 += ZKW1[ctr];
						ZKtemp2 = ZKfp[ctr]*g;
						if(ZKtemp1 == ZKtemp2 )//cout<<"================Verified (5)!!"<<endl;
						else //cout<<"================NOT NOT NOT Verified (5)!!"<<endl;
						tempB = 601;
						tempB = pow(tempB,pow(2,ctr))-1;
						ZKtemp1 = tempB * ZKB2[ctr];
						ZKtemp1 += g;//A
						ZKtemp1 *= ch;
						ZKtemp1 += ZKW2[ctr];
						ZKtemp2 = ZKfp[ctr]*h;
						ZKtemp3 = ZKwp[ctr]*g;
						ZKtemp2 += ZKtemp3;
						if(ZKtemp1 == ZKtemp2 )//cout<<"================Verified (6)!!"<<endl;
						else //cout<<"================NOT NOT NOT Verified (6)!!"<<endl;
					//check the last equation
						if(ctr ==0)prodw = ZKwp[ctr];
						else prodw = modmult(prodw,ZKwp[ctr],q);
						if(ctr ==0)prodf = ZKfp[ctr];
						else prodf = modmult(prodf,ZKfp[ctr],q);						
						tempB = pow(ch,ctr);
						if(ctr ==0){
							prodD1 = tempB * ZKD1[ctr];
							prodD2 = tempB * ZKD2[ctr];
						}
						else {
							prodD1 += tempB * ZKD1[ctr];
							prodD2 += tempB * ZKD2[ctr];							
						}
						
				}
				//check the last equation outside for loop ctr
				tempB = pow(ch,logm);
				E1 = tempB * E1;
				E2 = tempB * E2;	
				E1 += prodD1;
				E2 += prodD2;
				if(E1 == prodf * g )//cout<<"================Verified (7)!!"<<endl;
				else //cout<<"================NOT NOT NOT Verified (7)!!"<<endl;
				ZKtemp1 = prodf *h;
				ZKtemp1 += prodw *g;
				if(E2 == ZKtemp1 )//cout<<"================Verified (8)!!"<<endl;
				else //cout<<"================NOT NOT NOT Verified (8)!!"<<endl;
		*/		
				//////////////////////////////////////////////////////

		}
}

// Verify commitment - decommitment
bool VerifyCom(const CryptoRequest_VerifyComData& data){
		
		#ifndef MR_NOFULLWIDTH
		Miracl precision(50,0);
		#else 
		Miracl precision(50,MAXBASE);
		#endif
		
		Key key = data.key();
	    int iy,curve = key.curve();
		Big tempB,a,b,p,x,y,plain,rand;
		ECn g,h,c1,c2,tempE,a1,a2;
		miracl *mip=&precision;

		//cout<<"Verify commitment:"<<endl;
		//cout<< "PK: "<<key.pk().x()<<" "<<key.pk().y()<<endl;
		//cout<<"Curve: "<<curve<<endl;
		
		//Read g
		a=-3;
		mip->IOBASE=16;
		b= (char *)(ecb[curve].c_str());
		p=(char *)(ecp[curve].c_str());
		ecurve(a,b,p,MR_BEST);  // means use PROJECTIVE if possible, else AFFINE coordinates
		x=(char *)(ecx[curve].c_str());
		y=(char *)(ecy[curve].c_str());
		g=ECn(x,y);
		//Read PK
		mip->IOBASE=64;
		x = (char *)key.pk().x().c_str();
		iy = key.pk().y();
		h = ECn(x,iy); //decompress pk
		
		//Read cipher and plaintext, and verify
		Com com = data.com();
		x = (char *)com.c1().x().c_str();
		iy = com.c1().y();
		c1 = ECn(x,iy); //decompress
		x = (char *)com.c2().x().c_str();
		iy = com.c2().y();
		c2 = ECn(x,iy); //decompress	
		Decom decom = data.decom();
		plain = (char *)decom.msg().c_str();
		rand = (char *)decom.randomness().c_str();		
		//check
		a1 = rand*g;
		tempE = rand*h;
		a2 = plain*g;
		a2+=tempE;
		if(c1 == a1 && c2 == a2 ){
			return true;
		}
		else{
			return false;
		}
}

