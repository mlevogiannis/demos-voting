/* File: crypto.hpp */

#include "protobuf/crypto.pb.h"

void KeyGen(const CryptoRequest_KeyGenData& data, Key* key);
void GenBallot(const CryptoRequest_GenBallotData& data, CryptoResponse_BallotData* ballot_data, unsigned int copies);
void AddCom(const CryptoRequest_AddComData& data, Com* added_com);
void AddDecom(const CryptoRequest_AddDecomData& data, Decom* added_decom);
void CompleteZK(const CryptoRequest_CompleteZKData& data, CryptoResponse_ZKSet* zk_set);
bool VerifyCom(const CryptoRequest_VerifyComData& data);
