/* File: CryptoServer.hpp */

#ifndef CRYPTO_SERVER_HPP
#define CRYPTO_SERVER_HPP

#include <string>
#include <memory>
#include "ThreadPool.hpp"
#include "protobuf/crypto.pb.h"

class CryptoServer {

public:
	
	enum class AF {UNIX, IPv4, IPv6};
	
	// Unix Domain Sockets constructor
	CryptoServer(std::shared_ptr<ThreadPool> thread_pool, AF af, std::string path, const bool *server_stop = nullptr);
	
	// IPv4/IPv6 Sockets constructor
	CryptoServer(std::shared_ptr<ThreadPool> thread_pool, AF af, std::string ip, uint16_t port, const bool *server_stop = nullptr);
	
	void accept();
	~CryptoServer();
	
private:
	
	int sock_fd;
	const bool *server_stop;
	std::shared_ptr<ThreadPool> thread_pool;
	
	class ConsumerTask : public ThreadPool::ConsumerTask {
	public:
		ConsumerTask(int newsock_fd, size_t data_len, std::unique_ptr<CryptoRequest> req, size_t total_workers);
		~ConsumerTask();
		void consume(size_t curr_worker, size_t total_workers);
	private:
		const int newsock_fd;
		const size_t data_len;
		size_t remaining_workers;
		std::unique_ptr<CryptoRequest> req;
		std::unique_ptr<CryptoResponse> res;
	};
	
	class ProducerTask : public ThreadPool::ProducerTask {
	public:
		ProducerTask(int newsock_fd);
		std::unique_ptr<ThreadPool::ConsumerTask> produce(size_t thread_pool_size);
	private:
		const int newsock_fd;
	};
};

#endif // CRYPTO_SERVER_HPP
