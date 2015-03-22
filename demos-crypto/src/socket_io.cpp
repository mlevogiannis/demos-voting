/* File: socket_io.cpp */

#include <stdexcept>
#include <system_error>

#include <errno.h>
#include <sys/socket.h>

#include "socket_io.hpp"

using namespace std;


ssize_t recv_all(int sockfd, void *buf, size_t len, int flags)
{
	ssize_t ret;
	size_t sum = 0;
	
	while (sum < len)
	{
		ret = recv(sockfd, static_cast<char*>(buf)+sum, len-sum, flags);
		
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
	
	while (sum < len)
	{
		ret = send(sockfd, static_cast<const char*>(buf)+sum, len-sum, flags);
		
		if (ret == -1 && errno != EINTR)
			break;
		
		else if (ret > 0)
			sum += ret;
	}
	
	return ret > 0 ? sum : ret;
}


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

