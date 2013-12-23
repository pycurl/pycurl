#include <winsock2.h>
#include <assert.h>

#define sassert assert

void dump() {
	int err;
	LPTSTR buf;
	err = WSAGetLastError();
	FormatMessage(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM, NULL, err, 0, &buf, 0, NULL);
	printf("%d %s\n", err, buf);
	LocalFree(buf);
}

int main() {
	SOCKET s1, s2, s1d, s2d;
	int val, rv, size;
	WSADATA wsadata;
	WSAPROTOCOL_INFO pi;

	rv = WSAStartup(MAKEWORD(2, 2), &wsadata);
	assert(!rv);

	s1 = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
	assert(s1 > 0);
	val = 1;
	rv = setsockopt(s1, SOL_SOCKET, SO_KEEPALIVE, &val, sizeof(val));
	dump();
	sassert(!rv);

	s2 = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
	assert(s2 > 0);
	val = 0;
	rv = setsockopt(s2, SOL_SOCKET, SO_KEEPALIVE, &val, sizeof(val));
	sassert(!rv);

	size = sizeof(val);
	rv = getsockopt(s1, SOL_SOCKET, SO_KEEPALIVE, &val, &size);
	assert(!rv);
	printf("%d\n", val);
	sassert(val == 1);

	rv = getsockopt(s2, SOL_SOCKET, SO_KEEPALIVE, &val, &size);
	assert(!rv);
	sassert(val == 0);

	rv = WSADuplicateSocket(s1, GetCurrentProcessId(), &pi);
	assert(!rv);
	s1d = WSASocket(AF_INET, SOCK_STREAM, IPPROTO_TCP, &pi, 0, WSA_FLAG_OVERLAPPED);
	assert(s1d > 0);
	
	rv = getsockopt(s1d, SOL_SOCKET, SO_KEEPALIVE, &val, &size);
	assert(!rv);
	printf("%d\n", val);
	sassert(val == 1);

	rv = WSADuplicateSocket(s2, GetCurrentProcessId(), &pi);
	assert(!rv);
	s2d = WSASocket(AF_INET, SOCK_STREAM, IPPROTO_TCP, &pi, 0, WSA_FLAG_OVERLAPPED);
	assert(s2d > 0);
	
	rv = getsockopt(s2d, SOL_SOCKET, SO_KEEPALIVE, &val, &size);
	assert(!rv);
	printf("%d\n", val);
	sassert(val == 0);
}
