CXX = g++
CXXFLAGS = -Wall -std=c++11
LDFLAGS = -D_REENTRANT
LDLIBS = -lpthread -lprotobuf
RM = rm -f

default: miracl protobuf demos-crypto
all: default

.PHONY: miracl
.PHONY: protobuf

demos-crypto: main.o crypto.o CryptoServer.o socket_io.o ThreadPool.o \
 miracl/miracl.a protobuf/crypto.pb.o
	$(CXX) $(LDFLAGS) $(LDLIBS) $^ -o $@

main.o: main.cpp ThreadPool.hpp CryptoServer.hpp protobuf miracl
	$(CXX) $(CXXFLAGS) -c $< -o $@

crypto.o: crypto.cpp miracl/ecn.h miracl/big.h miracl protobuf \
 crypto.hpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

CryptoServer.o: CryptoServer.cpp crypto.hpp protobuf \
 socket_io.hpp ThreadPool.hpp CryptoServer.hpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

socket_io.o: socket_io.cpp socket_io.hpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

ThreadPool.o: ThreadPool.cpp ThreadPool.hpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

miracl:
	$(MAKE) -C ./miracl/

protobuf:
	$(MAKE) -C ./protobuf/

miracl/miracl.a: miracl

protobuf/crypto.pb.o: protobuf

clean:
	$(MAKE) -C ./miracl/ clean
	$(MAKE) -C ./protobuf/ clean
	$(RM) main.o crypto.o CryptoServer.o socket_io.o ThreadPool.o demos-crypto

