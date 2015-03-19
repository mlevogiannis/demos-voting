CXX = g++
CXXFLAGS = 
PROTOC = protoc
RM = rm -f

default: crypto.pb.o
all: default

crypto.pb.cc crypto.pb.h: crypto.proto
	$(PROTOC) --cpp_out=. crypto.proto

crypto.pb.o: crypto.pb.cc crypto.pb.h
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	$(RM) crypto.pb.o crypto.pb.cc crypto.pb.h
