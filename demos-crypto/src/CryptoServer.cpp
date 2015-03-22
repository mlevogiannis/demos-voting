/* File: CryptoServer.cpp */

#include <cmath>
#include <string>
#include <memory>
#include <stdexcept>
#include <system_error>

#include <errno.h>
#include <unistd.h>
#include <signal.h>
#include <sys/un.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <netinet/in.h>

#include "crypto.hpp"
#include "socket_io.hpp"
#include "ThreadPool.hpp"
#include "CryptoServer.hpp"
#include "protobuf/crypto.pb.h"

#define BACKLOG 128
#define MAXRECV 16777216	// bytes
#define TIMEOUT 300			// seconds

using namespace std;


CryptoServer::CryptoServer(shared_ptr<ThreadPool> thread_pool, AF af, string path, const bool *server_stop) :
	sock_fd(-1), server_stop(server_stop), thread_pool(thread_pool)
{
	// Unix Domain Sockets
	
	struct sockaddr_un sa;
	memset(&sa, 0, sizeof(sa));
	
	if (af != AF::UNIX)
		throw invalid_argument("Invalid address_family");
	
	// Verify that path can fit in sockaddr_un.sun_path
	
	if (path.size() > sizeof(sa.sun_path) - 1)
		throw invalid_argument("The socket path must be less than "
			+ to_string(sizeof(sa.sun_path)) + " characters long");
	
	// Initialize sockaddr_un structure
	
	sa.sun_family = AF_UNIX;
	path.copy(sa.sun_path, sizeof(sa.sun_path) - 1);
	sa.sun_path[path.size()] = '\0';
	
	// Unlink previous socket file (if any)
	
	if (unlink(path.c_str()) == -1 && errno != ENOENT)
		throw system_error(errno, system_category(), "unlink");
	
	// Create new socket
	
	if ((sock_fd = socket(AF_UNIX, SOCK_STREAM, 0)) == -1)
		throw system_error(errno, system_category(), "socket");
	
	// Set socket REUSEADDR option
	
	int opt = SO_REUSEADDR;
	setsockopt(sock_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
	
	// Bind socket to address
	
	if (bind(sock_fd, (struct sockaddr*) &sa, sizeof(sa)) == -1)
		throw system_error(errno, system_category(), "bind");
	
	// Listen for connections
	
	if (listen(sock_fd, BACKLOG) == -1)
		throw system_error(errno, system_category(), "listen");
}

CryptoServer::CryptoServer(shared_ptr<ThreadPool> thread_pool, AF af, string ip, uint16_t port, const bool *server_stop) :
	sock_fd(-1), server_stop(server_stop), thread_pool(thread_pool)
{
	// IPv4/IPv6 Sockets
	
	struct addrinfo hints, *addrlist, *addr;
	memset(&hints, 0, sizeof(hints));
	
	int domain;
	
	if (af == AF::IPv4)
		domain = AF_INET;
	else if (af == AF::IPv6)
		domain = AF_INET6;
	else
		throw invalid_argument("Invalid address_family");
	
	// Initialize node, service and addrinfo structure
	
	hints.ai_family = domain;
	hints.ai_socktype = SOCK_STREAM;
	hints.ai_protocol = 0;
	
	string port_s(to_string(port));
	
	const char *node = nullptr;
	const char *service = port_s.c_str();
	
	if (!ip.empty())
	{
		node = ip.c_str();
		hints.ai_flags = AI_NUMERICHOST;
	}
	else hints.ai_flags = AI_PASSIVE;
	
	// Use getaddrinfo to fill addrinfo struct
	
	int ret;
	
	if ((ret = getaddrinfo(node, service, &hints, &addrlist)) != 0)
	{
		if (ret != EAI_SYSTEM)
			throw runtime_error("getaddrinfo: " + string(gai_strerror(ret)));
		else
			throw system_error(errno, system_category(), "getaddrinfo");
	}
	
	// Iterate over available addrinfos (only 1 for AI_NUMERICHOST)
	
	for (addr = addrlist; addr != NULL; addr = addr->ai_next)
	{
		// Create new socket */
		
		if ((sock_fd = socket(addr->ai_family, addr->ai_socktype, addr->ai_protocol)) == -1)
			continue;
		
		// Set socket REUSEADDR option
		
		int opt = SO_REUSEADDR;
		setsockopt(sock_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
		
		// Bind socket to address
		
		if (bind(sock_fd, addr->ai_addr, addr->ai_addrlen) == 0)
			break;
		
		close(sock_fd);
	}
	
	// Free addrinfo struct
	
	freeaddrinfo(addrlist);
	
	if (addr == NULL)
		throw system_error(errno, system_category(), "socket/bind");
	
	// Listen for connections
	
	if (listen(sock_fd, BACKLOG) == -1)
		throw system_error(errno, system_category(), "listen");
}

CryptoServer::~CryptoServer()
{
	shutdown(sock_fd, SHUT_RDWR);
	close(sock_fd);
}

void CryptoServer::accept()
{
	int newsock_fd;
	
	struct sockaddr_un client;
	socklen_t client_len = sizeof(struct sockaddr_un);
	
	struct timeval timeout;
	socklen_t optlen = sizeof(timeout);
	
	timeout.tv_sec = TIMEOUT;
	timeout.tv_usec = 0;
	
	// Main server loop
	
	while (true)
	{
		// Check server_stop condition
		
		if (server_stop != nullptr && *server_stop == true)
			break;
		
		// Accept connections
		
		if ((newsock_fd = ::accept(sock_fd, (struct sockaddr*) &client, &client_len)) == -1)
			continue;
		
		// Set receive/send timeouts
		
		setsockopt(newsock_fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, optlen);
		setsockopt(newsock_fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, optlen);
		
		// Create a new ProducerTask and add in the ThreadPool
		
		unique_ptr<ProducerTask> producer_task(new ProducerTask(newsock_fd));
		thread_pool->add_task(move(producer_task));
	}
}


CryptoServer::ProducerTask::ProducerTask(int newsock_fd) :
	ThreadPool::ProducerTask(), newsock_fd(newsock_fd) { }

unique_ptr<ThreadPool::ConsumerTask> CryptoServer::ProducerTask::produce(size_t thread_pool_size)
{
	try
	{
		ssize_t ret;
		uint32_t req_size;
		
		// Receive the size of the request
		
		ret = recv_all_w(newsock_fd, &req_size, sizeof(uint32_t), 0);
		req_size = ntohl(req_size);
		
		if (req_size < 1 || req_size > MAXRECV)
			throw range_error("req_size out of range");
		
		// Receive the request (req_size bytes)
		
		unique_ptr<char[]> buffer(new char[req_size]);
		
		ret = recv_all_w(newsock_fd, buffer.get(), req_size, 0);
		string data(buffer.get(), ret);
		
		// Parse the received request
		
		unique_ptr<CryptoRequest> req(new CryptoRequest());
		req->ParseFromString(data);
		
		// Check if the task can be parallelized
		
		size_t data_len = 1;
		size_t total_workers = 1;
		
		if (req->command() == CryptoRequest_CMD_GenBallot)
		{
			data_len = req->gb().number();
			total_workers = thread_pool_size > data_len ? data_len : thread_pool_size;
		}
		
		// Return a ConsumerTask
		
		unique_ptr<ConsumerTask> consumer_task(new ConsumerTask(newsock_fd, data_len, move(req), total_workers));
		return move(consumer_task);
	}
	catch (...)
	{
		shutdown(newsock_fd, SHUT_RDWR);
		close(newsock_fd);
		throw;
	}
}


CryptoServer::ConsumerTask::ConsumerTask(int newsock_fd, size_t data_len,
	unique_ptr<CryptoRequest> req, size_t total_workers) :
	ThreadPool::ConsumerTask(total_workers), newsock_fd(newsock_fd),
	data_len(data_len), remaining_workers(total_workers), req(move(req)),
	res(new CryptoResponse()) { }

CryptoServer::ConsumerTask::~ConsumerTask()
{
	shutdown(newsock_fd, SHUT_RDWR);
	close(newsock_fd);
}

void CryptoServer::ConsumerTask::consume(size_t curr_worker, size_t total_workers)
{
	bool send = false;
	
	// Calculate current worker's data slice
	
	size_t worker_data = data_len;
	
	if (total_workers > 1)
	{
		size_t _curr_worker = 0;
		size_t _data_len = data_len;
		
		while (_curr_worker <= curr_worker)
		{
			worker_data = static_cast<size_t>(ceil(_data_len / (total_workers - _curr_worker)));
		
			_curr_worker++;
			_data_len -= worker_data;
		}
	}
	
	// Execute command
	
	if (req->command() == CryptoRequest_CMD_KeyGen && req->has_kg())
	{
		CryptoRequest_KeyGenData keydata = req->kg();
		Key key = KeyGen(keydata.n(), keydata.m());
		res->mutable_key()->CopyFrom(key);
		send = true;
	}
	else if (req->command() == CryptoRequest_CMD_GenBallot && req->has_gb())
	{
		CryptoRequest_GenBallotData genballotdata = req->gb();
		CryptoResponse_Ballots ballots = GenBallot(genballotdata.key(), genballotdata.n(), genballotdata.m(), worker_data);
		
		// Acquire the lock
		
		mutex_lock();
		
		CryptoResponse_Ballots *res_ballots = res->mutable_ballots();
		
		// Insert results in the response
		
		for(int i = 0; i < ballots.eachballot_size(); i++)
		{
			const CryptoResponse_Ballots_SetB &eachballot = ballots.eachballot(i);
			CryptoResponse_Ballots_SetB *res_eachballot = res_ballots->add_eachballot();
			
			res_eachballot->CopyFrom(eachballot);
		}
		
		// Only the last worker sends the response
		
		if(--remaining_workers == 0)
			send = true;
		
		mutex_unlock();
	}
	else if (req->command() == CryptoRequest_CMD_AddCom && req->has_ab())
	{
		CryptoRequest_AddComData addcomdata = req->ab();
		Com sum = AddCom(addcomdata);
		res->mutable_gcombined()->CopyFrom(sum);
		send = true;
	}
	else if (req->command() == CryptoRequest_CMD_AddDecom && req->has_ad())
	{
		CryptoRequest_AddDecomData adddecomdata = req->ad();
		Decom sum = AddDecom(adddecomdata);
		res->mutable_zcombined()->CopyFrom(sum);
		send = true;
	}
	else if (req->command() == CryptoRequest_CMD_VerifyCom && req->has_vc())
	{
		CryptoRequest_VerifyComData verifydata = req->vc();
		bool check = VerifyCom(verifydata);
		res->set_check(check);
		send = true;
	}
	else if (req->command() == CryptoRequest_CMD_CompleteZK && req->has_cz())
	{
		CryptoRequest_CompleteZKData zkdata = req->cz();
		CryptoResponse_ZK_set zk2 = CompleteZK(zkdata);
		res->mutable_zk_set()->CopyFrom(zk2);
		send = true;
	}
	
	// Serialize and send response
	
	if (send)
	{
		string data;
		uint32_t res_size;
		
		res->SerializeToString(&data);
		
		unique_ptr<char[]> buffer(new char[data.size()]);
		data.copy(buffer.get(), data.size());
		
		res_size = htonl(data.size());
		
		send_all_w(newsock_fd, &res_size, sizeof(uint32_t), 0);
		send_all_w(newsock_fd, buffer.get(), data.size(), 0);
	}
}

