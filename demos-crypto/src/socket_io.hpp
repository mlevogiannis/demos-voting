/* File: socket_io.hpp */

#ifndef SOCKET_IO_HPP
#define SOCKET_IO_HPP


/*
 * Function: recv_all
 * ------------------
 *  Receives data from sockfd until either len bytes have been received or an
 *  error occurs, restarting on any signal interrupts. Returns the number of
 *  bytes received, 0 if the peer has performed an orderly shutdown, or -1 and
 *  sets errno to indicate the error. See recv for more information.
 */

ssize_t recv_all(int sockfd, void *buf, size_t len, int flags);


/*
 * Function: send_all
 * ------------------
 *  Sends data from buf until either all data has been sent or an error occurs,
 *  restarting on any signal interrupts. Returns the number of bytes sent, or -1
 *  and sets errno to indicate the error. See send for more information.
 */

ssize_t send_all(int sockfd, const void *buf, size_t len, int flags);


#endif // SOCKET_IO_HPP
