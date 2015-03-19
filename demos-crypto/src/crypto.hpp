/* File: crypto.hpp */

#include "protobuf/crypto.pb.h"

Key KeyGen(int N, int m);
CryptoResponse_Ballots GenBallot(Key key, int N, int m, int copies);
Com AddCom(CryptoRequest_AddComData data);
Decom AddDecom(CryptoRequest_AddDecomData data);
CryptoResponse_ZK_set CompleteZK(CryptoRequest_CompleteZKData data);
bool VerifyCom(CryptoRequest_VerifyComData data);
