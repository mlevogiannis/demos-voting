/* File: ThreadPool.hpp */

#ifndef THREAD_POOL_HPP
#define THREAD_POOL_HPP

#include <queue>
#include <memory>
#include <pthread.h>

class ThreadPool {
	
public:
	
	class ConsumerTask {
	public:
		ConsumerTask(size_t total_workers = 1);
		virtual ~ConsumerTask();
		virtual void consume(size_t curr_worker, size_t total_workers) = 0;
		
	protected:
		void mutex_lock();
		void mutex_unlock();
		
	private:
		size_t curr_worker;
		const size_t total_workers;
		pthread_mutex_t mutex;
		
		friend ThreadPool;
	};
	
	class ProducerTask {
	public:
		ProducerTask();
		virtual ~ProducerTask();
		virtual std::unique_ptr<ConsumerTask> produce(size_t thread_pool_size) = 0;
	};
	
	ThreadPool(size_t thread_pool_size);
	~ThreadPool();
	
	void add_task(std::unique_ptr<ProducerTask> producer_task);
	size_t size() const;
	
private:
	
	const size_t thread_pool_size;
	std::vector<pthread_t> thread_pool;
	
	struct ThreadVars {
		
		std::queue<std::shared_ptr<ConsumerTask>> task_queue;
		
		pthread_cond_t cond;
		pthread_mutex_t mutex;
		
		bool thread_stop;
		
		ThreadVars();
	};
	
	std::shared_ptr<ThreadVars> thread_vars;
	
	static void* producer(void *argp);
	static void* consumer(void *argp);
	
	struct ProducerVars {
		size_t thread_pool_size;
		std::shared_ptr<ThreadVars> thread_vars;
		std::unique_ptr<ProducerTask> producer_task;
		ProducerVars(std::shared_ptr<ThreadVars> thread_vars,
			std::unique_ptr<ProducerTask> producer_task, size_t thread_pool_size);
	};
	
	struct ConsumerVars {
		std::shared_ptr<ThreadVars> thread_vars;
		ConsumerVars(std::shared_ptr<ThreadVars> thread_vars);
	};
};

#endif // THREAD_POOL_HPP
