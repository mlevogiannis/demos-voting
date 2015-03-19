/* File: ThreadPool.cpp */

#include <queue>
#include <memory>
#include <stdexcept>
#include <system_error>

#include <signal.h>
#include <pthread.h>

#include "ThreadPool.hpp"

using namespace std;


// ThreadPool member methods ---------------------------------------------------

ThreadPool::ThreadPool(size_t thread_pool_size) :
	thread_pool_size(thread_pool_size), thread_vars(new ThreadVars())
{
	if (thread_pool_size < 1)
		throw invalid_argument("The size of the thread pool must be strictly positive");
	
	// New threads inherit a copy of their creator's signal mask.
	// Block all signals before starting the consumer threads.
	
	sigset_t old_sigset, new_sigset;
	
	sigfillset(&new_sigset);
	pthread_sigmask(SIG_SETMASK, &new_sigset, &old_sigset);
	
	// Initialize the consumer thread pool
	
	for (size_t i = 0; i < thread_pool_size; i++)
	{
		int t_errno;
		pthread_t thread;
		ConsumerVars *consumer_vars;
		
		consumer_vars = new ConsumerVars(thread_vars);
		
		if ((t_errno = pthread_create(&thread, nullptr, consumer, consumer_vars)))
			throw system_error(t_errno, system_category(), "pthread_create");
		
		thread_pool.push_back(thread);
	}
	
	// Restore old signal mask
	
	pthread_sigmask(SIG_SETMASK, &old_sigset, nullptr);
}

ThreadPool::~ThreadPool()
{
	// Get references to thread_vars members
	
	pthread_cond_t &cond = thread_vars->cond;
	pthread_mutex_t &mutex = thread_vars->mutex;
	
	bool &thread_stop = thread_vars->thread_stop;
	
	// Lock the mutex
	
	pthread_mutex_lock(&mutex);
	
	// Order consumer threads to terminate
	
	thread_stop = true;
	pthread_cond_broadcast(&cond);
	
	// Unlock the mutex
	
	pthread_mutex_unlock(&mutex);
	
	// Wait for all consumer threads to terminate
	
	for (size_t i = 0; i < thread_pool_size; i++)
		pthread_join(thread_pool[i], nullptr);
	
	// TODO: Also wait for remaining producer threads
}

void ThreadPool::add_task(unique_ptr<ProducerTask> producer_task)
{
	// New threads inherit a copy of their creator's signal mask.
	// Block all signals before starting the producer thread.
	
	sigset_t old_sigset, new_sigset;
	
	sigfillset(&new_sigset);
	pthread_sigmask(SIG_SETMASK, &new_sigset, &old_sigset);
	
	// Start the new producer thread
	
	int t_errno;
	pthread_t thread;
	ProducerVars *producer_vars;
	
	producer_vars = new ProducerVars(thread_vars, move(producer_task), thread_pool_size);
	
	if ((t_errno = pthread_create(&thread, nullptr, producer, producer_vars)))
		throw system_error(t_errno, system_category(), "pthread_create");
	
	// Restore old signal mask
	
	pthread_sigmask(SIG_SETMASK, &old_sigset, nullptr);
}

size_t ThreadPool::size() const
{
	return thread_pool_size;
}


// ThreadPool static methods ---------------------------------------------------

void* ThreadPool::producer(void *argp)
{
	pthread_detach(pthread_self());
	
	// Get producer arguments and free allocated memory
	
	ProducerVars *producer_vars = static_cast<ProducerVars*>(argp);
	
	size_t thread_pool_size = producer_vars->thread_pool_size;
	shared_ptr<ThreadVars> thread_vars = producer_vars->thread_vars;
	unique_ptr<ProducerTask> producer_task = move(producer_vars->producer_task);
	
	delete producer_vars;
	
	// Get references to thread_vars members
	
	queue<shared_ptr<ConsumerTask>> &task_queue = thread_vars->task_queue;
	
	pthread_cond_t &cond = thread_vars->cond;
	pthread_mutex_t &mutex = thread_vars->mutex;
	
	const bool &thread_stop = thread_vars->thread_stop;
	
	// "Produce" a new task
	
	unique_ptr<ConsumerTask> consumer_task;
	
	try { consumer_task = producer_task->produce(thread_pool_size); }
	catch (...) { pthread_exit(nullptr); }
	
	// Lock the task queue mutex
	
	pthread_mutex_lock(&mutex);
	
	// Check stop condition
	
	if (thread_stop)
	{
		pthread_mutex_unlock(&mutex);
		pthread_exit(nullptr);
	}
	
	// Critical section: add task at the end of the queue
	
	task_queue.push(move(consumer_task));
	
	// Notify consumers if the task queue was previously empty
	
	if (task_queue.size() == 1)
		pthread_cond_broadcast(&cond);
	
	// Unlock the task queue mutex and exit
	
	pthread_mutex_unlock(&mutex);
	pthread_exit(nullptr);
}

void* ThreadPool::consumer(void *argp)
{
	// Get consumer arguments and free allocated memory
	
	ConsumerVars *consumer_vars = static_cast<ConsumerVars*>(argp);
	shared_ptr<ThreadVars> thread_vars = consumer_vars->thread_vars;
	delete consumer_vars;
	
	// Get references to thread_vars members
	
	queue<shared_ptr<ConsumerTask>> &task_queue = thread_vars->task_queue;
	
	pthread_cond_t &cond = thread_vars->cond;
	pthread_mutex_t &mutex = thread_vars->mutex;
	
	const bool &thread_stop = thread_vars->thread_stop;
	
	// Main consumer loop
	
	while (true)
	{
		// Lock the task queue mutex
		
		pthread_mutex_lock(&mutex);
		
		// Block if the task queue is empty
		
		while (!thread_stop && task_queue.size() == 0)
			pthread_cond_wait(&cond, &mutex);
		
		// Check stop condition
		
		if (thread_stop)
		{
			pthread_mutex_unlock(&mutex);
			break;
		}
		
		// Critical section: get task from the head of the queue
		
		size_t total_workers, curr_worker;
		shared_ptr<ConsumerTask> consumer_task;
		
		consumer_task = task_queue.front();
		
		curr_worker = consumer_task->curr_worker;
		total_workers = consumer_task->total_workers;
		
		consumer_task->curr_worker++;
		
		if (consumer_task->curr_worker == consumer_task->total_workers)
			task_queue.pop();
		
		// Unlock the task queue mutex
		
		pthread_mutex_unlock(&mutex);
		
		// "Consume" the task
		
		try { consumer_task->consume(curr_worker, total_workers); }
		catch (...) { continue; }
		
	}
	
	pthread_exit(nullptr);
}


// ProducerTask and ConsumerTask member methods --------------------------------

ThreadPool::ProducerTask::ProducerTask() { }
ThreadPool::ProducerTask::~ProducerTask() { }

ThreadPool::ConsumerTask::ConsumerTask(size_t total_workers) :
	curr_worker(0), total_workers(total_workers), mutex(PTHREAD_MUTEX_INITIALIZER)
{
	if (total_workers < 1)
		throw invalid_argument("The number of ConsumerTask workers must be strictly positive");
}

ThreadPool::ConsumerTask::~ConsumerTask() { }

void ThreadPool::ConsumerTask::mutex_lock()
{
	pthread_mutex_lock(&mutex);
}

void ThreadPool::ConsumerTask::mutex_unlock()
{
	pthread_mutex_unlock(&mutex);
}


// ThreadVars, ProducerVars and ConsumerVars member methods --------------------

ThreadPool::ThreadVars::ThreadVars() :
	cond(PTHREAD_COND_INITIALIZER), mutex(PTHREAD_MUTEX_INITIALIZER),
	thread_stop(false) { }

ThreadPool::ProducerVars::ProducerVars(shared_ptr<ThreadVars> thread_vars,
	unique_ptr<ProducerTask> producer_task, size_t thread_pool_size) :
	thread_pool_size(thread_pool_size), thread_vars(thread_vars),
	producer_task(move(producer_task)) { }

ThreadPool::ConsumerVars::ConsumerVars(shared_ptr<ThreadVars> thread_vars) :
	thread_vars(thread_vars) { }

