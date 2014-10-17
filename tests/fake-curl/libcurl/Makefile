all: \
	with_gnutls.so \
	with_nss.so \
	with_openssl.so \
	with_unknown_ssl.so \
	without_ssl.so

.SUFFIXES: .c .so

.c.so:
	`curl-config --cc` `curl-config --cflags` -shared -fPIC \
		-Wl,-soname,$@ -o $@ $<

show-targets:
	ls *c |sed -e 's/.c$$/.so/' | awk '{print $$1 " \\"}'
