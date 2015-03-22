/* File: socket_io.cpp */

#include <stdexcept>
#include <system_error>

#include <time.h>
#include <errno.h>
#include <unistd.h>
#include <sys/time.h>
#include <sys/socket.h>

#include "socket_io.hpp"

#if _POSIX_TIMERS > 0 && defined (_POSIX_MONOTONIC_CLOCK)
	#define SOCK_TIMEOUT
#else
	#undef SOCK_TIMEOUT
#endif

using namespace std;


#ifdef SOCK_TIMEOUT

// Timespec functions ----------------------------------------------------------

void timespec_init(struct timespec *t)
{
	t->tv_sec = 0;
	t->tv_nsec = 0;
}

void timeval_to_timespec(const struct timeval *tv, struct timespec *ts)
{
	ts->tv_sec = tv->tv_sec;
	ts->tv_nsec = tv->tv_usec * 1000;
}

void timespec_add(struct timespec *t1, struct timespec *t2)
{
	t1->tv_sec = t1->tv_sec + t2->tv_sec;
	t1->tv_nsec = t1->tv_nsec + t2->tv_nsec;
	
	if (t1->tv_nsec >= 1000000000)
	{
		t1->tv_sec++;
		t1->tv_nsec -= 1000000000;
	}
}

void timespec_sub(struct timespec *t1, struct timespec *t2)
{
	t1->tv_sec = t1->tv_sec - t2->tv_sec;
	t1->tv_nsec = t1->tv_nsec - t2->tv_nsec;
	
	if (t1->tv_nsec < 0)
	{
		t1->tv_sec--;
		t1->tv_nsec += 1000000000;
	}
}

int timespec_cmp_lt(const struct timespec *t1, const struct timespec *t2)
{
	return ((t1->tv_sec == t2->tv_sec) ?
		(t1->tv_nsec < t2->tv_nsec) : (t1->tv_sec < t2->tv_sec));
}

#endif


// Receive/Send functions ------------------------------------------------------

ssize_t recv_all(int sockfd, void *buf, size_t len, int flags)
{
	ssize_t ret;
	size_t sum = 0;
	
#ifdef SOCK_TIMEOUT
	
	// Get socket's recv timeout
	
	struct timeval timeout_tv;
	socklen_t optlen = sizeof(timeout_tv);
	
	getsockopt(sockfd, SOL_SOCKET, SO_RCVTIMEO, &timeout_tv, &optlen);
	
	// Convert timeout from timeval to timespec
	
	struct timespec timeout, elapsed, t1, t2;
	
	timespec_init(&elapsed);
	timeval_to_timespec(&timeout_tv, &timeout);
	
	// Receive loop
	
	while (sum < len)
	{
		// Check if timer has expired
		
		if(timespec_cmp_lt(&timeout, &elapsed))
		{
			errno = EAGAIN;
			ret = -1;
			break;
		}
		
		// Time and receive data
		
		clock_gettime(CLOCK_MONOTONIC, &t1);
		ret = recv(sockfd, static_cast<char*>(buf)+sum, len-sum, flags);
		clock_gettime(CLOCK_MONOTONIC, &t2);
		
		timespec_sub(&t2, &t1);
		timespec_add(&elapsed, &t2);
		
#else
	
	while (sum < len)
	{
		ret = recv(sockfd, static_cast<char*>(buf)+sum, len-sum, flags);
	
#endif
		
		// Handle recv return value
		
		if ((ret == -1 && errno != EINTR) || ret == 0)
			break;
		
		else if (ret > 0)
			sum += ret;
	}
	
	return ret > 0 ? sum : ret;
}

ssize_t send_all(int sockfd, const void *buf, size_t len, int flags)
{
	ssize_t ret;
	size_t sum = 0;
	
#ifdef SOCK_TIMEOUT
	
	// Get socket's send timeout
	
	struct timeval timeout_tv;
	socklen_t optlen = sizeof(timeout_tv);
	
	getsockopt(sockfd, SOL_SOCKET, SO_SNDTIMEO, &timeout_tv, &optlen);
	
	// Convert timeout from timeval to timespec
	
	struct timespec timeout, elapsed, t1, t2;
	
	timespec_init(&elapsed);
	timeval_to_timespec(&timeout_tv, &timeout);
	
	// Send loop
	
	while (sum < len)
	{
		// Check if timer has expired
		
		if(timespec_cmp_lt(&timeout, &elapsed))
		{
			errno = EAGAIN;
			ret = -1;
			break;
		}
		
		// Time and send data
		
		clock_gettime(CLOCK_MONOTONIC, &t1);
		ret = send(sockfd, static_cast<const char*>(buf)+sum, len-sum, flags);
		clock_gettime(CLOCK_MONOTONIC, &t2);
		
		timespec_sub(&t2, &t1);
		timespec_add(&elapsed, &t2);
		
#else
	
	while (sum < len)
	{
		ret = send(sockfd, static_cast<const char*>(buf)+sum, len-sum, flags);
	
#endif
		
		// Handle send return value
		
		if (ret == -1 && errno != EINTR)
			break;
		
		else if (ret > 0)
			sum += ret;
	}
	
	return ret > 0 ? sum : ret;
}


// Receive/Send wrapper functions ----------------------------------------------

ssize_t recv_all_w(int sockfd, void *buf, size_t len, int flags)
{
	ssize_t ret = recv_all(sockfd, buf, len, flags);
	
	if (ret == 0)
		throw runtime_error("recv: Connection closed");
	
	else if (ret == -1)
		throw system_error(errno, system_category(), "recv");
	
	return ret;
}

ssize_t send_all_w(int sockfd, const void *buf, size_t len, int flags)
{
	ssize_t ret = send_all(sockfd, buf, len, flags);
	
	if (ret == -1)
		throw system_error(errno, system_category(), "send");
	
	return ret;
}

