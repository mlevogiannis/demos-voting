CXX = g++
CXXFLAGS = -m64 -O2
RM = rm -f

default: miracl.a
all: default

miracl.a:
	$(RM) miracl.a
	cp mirdef.hpp mirdef.h
	$(CXX) $(CXXFLAGS) -c mrcore.c
	$(CXX) $(CXXFLAGS) -c mrarth0.c
	$(CXX) $(CXXFLAGS) -c mrarth1.c
	$(CXX) $(CXXFLAGS) -c mrarth2.c
	$(CXX) $(CXXFLAGS) -c mralloc.c
	$(CXX) $(CXXFLAGS) -c mrsmall.c
	$(CXX) $(CXXFLAGS) -c mrio1.c
	$(CXX) $(CXXFLAGS) -c mrio2.c
	$(CXX) $(CXXFLAGS) -c mrgcd.c
	$(CXX) $(CXXFLAGS) -c mrjack.c
	$(CXX) $(CXXFLAGS) -c mrxgcd.c
	$(CXX) $(CXXFLAGS) -c mrarth3.c
	$(CXX) $(CXXFLAGS) -c mrbits.c
	$(CXX) $(CXXFLAGS) -c mrrand.c
	$(CXX) $(CXXFLAGS) -c mrprime.c
	$(CXX) $(CXXFLAGS) -c mrcrt.c
	$(CXX) $(CXXFLAGS) -c mrscrt.c
	$(CXX) $(CXXFLAGS) -c mrmonty.c
	$(CXX) $(CXXFLAGS) -c mrpower.c
	$(CXX) $(CXXFLAGS) -c mrsroot.c
	$(CXX) $(CXXFLAGS) -c mrcurve.c
	$(CXX) $(CXXFLAGS) -c mrfast.c
	$(CXX) $(CXXFLAGS) -c mrshs.c
	$(CXX) $(CXXFLAGS) -c mrshs256.c
	$(CXX) $(CXXFLAGS) -c mrshs512.c
	$(CXX) $(CXXFLAGS) -c mrsha3.c
	$(CXX) $(CXXFLAGS) -c mrfpe.c
	$(CXX) $(CXXFLAGS) -c mraes.c
	$(CXX) $(CXXFLAGS) -c mrgcm.c
	$(CXX) $(CXXFLAGS) -c mrlucas.c
	$(CXX) $(CXXFLAGS) -c mrzzn2.c
	$(CXX) $(CXXFLAGS) -c mrzzn2b.c
	$(CXX) $(CXXFLAGS) -c mrzzn3.c
	$(CXX) $(CXXFLAGS) -c mrecn2.c
	$(CXX) $(CXXFLAGS) -c mrstrong.c
	$(CXX) $(CXXFLAGS) -c mrbrick.c
	$(CXX) $(CXXFLAGS) -c mrebrick.c
	$(CXX) $(CXXFLAGS) -c mrec2m.c
	$(CXX) $(CXXFLAGS) -c mrgf2m.c
	$(CXX) $(CXXFLAGS) -c mrflash.c
	$(CXX) $(CXXFLAGS) -c mrfrnd.c
	$(CXX) $(CXXFLAGS) -c mrdouble.c
	$(CXX) $(CXXFLAGS) -c mrround.c
	$(CXX) $(CXXFLAGS) -c mrbuild.c
	$(CXX) $(CXXFLAGS) -c mrflsh1.c
	$(CXX) $(CXXFLAGS) -c mrpi.c
	$(CXX) $(CXXFLAGS) -c mrflsh2.c
	$(CXX) $(CXXFLAGS) -c mrflsh3.c
	$(CXX) $(CXXFLAGS) -c mrflsh4.c
	cp mrmuldv.g64 mrmuldv.c
	$(CXX) $(CXXFLAGS) -c mrmuldv.c
	$(CXX) $(CXXFLAGS) -c big.cpp
	$(CXX) $(CXXFLAGS) -c zzn.cpp
	$(CXX) $(CXXFLAGS) -c ecn.cpp
	$(CXX) $(CXXFLAGS) -c ec2.cpp
	$(CXX) $(CXXFLAGS) -c flash.cpp
	$(CXX) $(CXXFLAGS) -c crt.cpp
	ar rc miracl.a mrcore.o mrarth0.o mrarth1.o mrarth2.o mralloc.o mrsmall.o mrzzn2.o mrzzn3.o
	ar r miracl.a mrio1.o mrio2.o mrjack.o mrgcd.o mrxgcd.o mrarth3.o mrbits.o mrecn2.o
	ar r miracl.a mrrand.o mrprime.o mrcrt.o mrscrt.o mrmonty.o mrcurve.o mrsroot.o mrzzn2b.o
	ar r miracl.a mrpower.o mrfast.o mrshs.o mrshs256.o mraes.o mrlucas.o mrstrong.o mrgcm.o
	ar r miracl.a mrflash.o mrfrnd.o mrdouble.o mrround.o mrbuild.o
	ar r miracl.a mrflsh1.o mrpi.o mrflsh2.o mrflsh3.o mrflsh4.o
	ar r miracl.a mrbrick.o mrebrick.o mrec2m.o mrgf2m.o mrmuldv.o mrshs512.o mrsha3.o mrfpe.o
	ar r miracl.a big.o zzn.o ecn.o ec2.o flash.o crt.o
	$(RM) *.o

clean:
	$(RM) miracl.a mirdef.h mrmuldv.c *.o
