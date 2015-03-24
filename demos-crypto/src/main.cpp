/* File: main.cpp */

#include <string>
#include <vector>
#include <memory>
#include <iostream>
#include <algorithm>
#include <stdexcept>

#include <unistd.h>
#include <signal.h>

#include "miracl/miracl.h"
#include "protobuf/crypto.pb.h"
#include "ThreadPool.hpp"
#include "CryptoServer.hpp"

using namespace std;


static bool sig_state = false;
static void sig_handler(int signo) { sig_state = true; }

int main(int argc, char **argv)
{
	uint16_t port;
	string path, ip;
	size_t thread_pool_size;
	
	CryptoServer::AF af;
	
	// Parse command line arguments
	
	try
	{
		int opt;
		opterr = 0;
		
		bool af_found = false;
		bool th_found = false;
		
		while ((opt = getopt(argc, argv, "s:t:h")) != -1)
		{
			switch (opt)
			{
				case 's':
				{
					if (af_found)
						throw invalid_argument("Option already set: -s");
					
					string optstr(optarg);
					
					// Get address_family
					
					vector<string>::iterator af_it;
					vector<string> af_val {"unix", "ipv4", "ipv6"};
					
					af_it = find(af_val.begin(), af_val.end(), optstr);
					
					if (af_it == af_val.end())
						throw invalid_argument("Invalid address_family: " + optstr);
					
					af = static_cast<CryptoServer::AF> (af_it - af_val.begin());
					
					// Get address_family options
					
					vector<string> af_options;
					
					while (optind < argc && (argv[optind][0] != '-' || argv[optind][1] == '\0'))
					{
						af_options.emplace_back(argv[optind]);
						optind++;
					}
					
					// Verify address_family options
					
					switch (af)
					{
						case CryptoServer::AF::UNIX:
							
							if (af_options.size() != 1)
								throw invalid_argument("Invalid option(s) for address_family: " + optstr);
							
							path = af_options[0];
							break;
						
						case CryptoServer::AF::IPv4:
						case CryptoServer::AF::IPv6:
							
							if (af_options.size() < 1 || af_options.size() > 2)
								throw invalid_argument("Invalid option(s) for address_family: " + optstr);
							
							size_t sz;
							string port_str;
							bool port_error = false;
							
							if (af_options.size() == 1)
							{
								ip.clear();
								port_str = af_options[0];
							}
							else if (af_options.size() == 2)
							{
								ip = af_options[0];
								port_str = af_options[1];
							}
							
							try { port = stoul(port_str, &sz); }
							catch (exception& e) { port_error = true; }
							
							if (port_error || port_str.size() != sz)
								throw invalid_argument("Invalid " + optstr + "_port: " + port_str);
							
							break;
					}
					
					af_found = true;
					break;
				}
				
				case 't':
				{
					if (th_found)
						throw invalid_argument("Option already set: -t");
					
					size_t sz;
					string thread_str(optarg);
					bool thread_error = false;
					
					// Get thread_pool_size
					
					try { thread_pool_size = stoul(thread_str, &sz); }
					catch (exception& e) { thread_error = true; }
					
					if (thread_error || thread_str.size() != sz)
						throw invalid_argument("Invalid thread_pool_size: " + thread_str);
					
					th_found = true;
					break;
				}
				
				case 'h':
				{
					cout << "Usage: demos-crypto -s unix <path> -t <threads>" << endl;
					cout << "                    -s ipv4 [<ip>] <port> -t <threads>" << endl;
					cout << "                    -s ipv6 [<ip>] <port> -t <threads>" << endl;
					return 0;
				}
				
				default: // '?'
				{
					throw invalid_argument("Invalid option: -" + string(1, optopt));
					break;
				}
			}
		}
		
		if (!af_found || !th_found)
		{
			cerr << "Missing options. Try -h for more information." << endl;
			return 1;
		}
	}
	catch (exception& e)
	{
		cerr << e.what() << endl;
		return 1;
	}
	
	struct sigaction act;
	
	// Ignore SIGPIPE
	
	act.sa_flags = 0;
	act.sa_handler = SIG_IGN;
	sigfillset(&(act.sa_mask));
	sigaction(SIGPIPE, &act, nullptr);
	
	// Handle SIGHUP, SIGINT, SIGQUIT and SIGTERM
	
	act.sa_flags = 0;
	act.sa_handler = &sig_handler;
	sigfillset(&(act.sa_mask));
	sigaction(SIGHUP, &act, nullptr);
	sigaction(SIGINT, &act, nullptr);
	sigaction(SIGQUIT, &act, nullptr);
	sigaction(SIGTERM, &act, nullptr);
	
	// MIRACL multi-threading init
	
	mr_init_threading();
	
	try
	{
		// Initialize the ThreadPool
		
		shared_ptr<ThreadPool> thread_pool(new ThreadPool(thread_pool_size));
		
		// Start the CryptoServer
		
		unique_ptr<CryptoServer> crypto_server;
		
		if (af == CryptoServer::AF::UNIX)
			crypto_server = unique_ptr<CryptoServer>(new CryptoServer(thread_pool, af, path, &sig_state));
		else // if (af == CryptoServer::AF::IPv4 || af == CryptoServer::AF::IPv6)
			crypto_server = unique_ptr<CryptoServer>(new CryptoServer(thread_pool, af, ip, port, &sig_state));
		
		crypto_server->accept();
	}
	catch (exception& e)
	{
		cerr << "Error: " << e.what() << endl;
		return 1;
	}
	
	// MIRACL and Protobuf shutdown
	
	mr_end_threading();
	google::protobuf::ShutdownProtobufLibrary();
	
	return 0;
}

