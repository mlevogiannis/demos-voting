/* File: socket_io.cpp */

#include <errno.h>
#include <sys/socket.h>

#include "socket_io.hpp"

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
		
		if (ret < 0 && errno != EINTR)
			break;
		
		else if (ret > 0)
			sum += ret;
	}
	
	return ret > 0 ? sum : ret;
}
