ALL = \
	with_gnutls.so \
	with_nss.so \
	with_openssl.so \
	with_unknown_ssl.so \
	without_ssl.so

all: $(ALL)
clean:
	rm -f $(ALL)

.SUFFIXES: .c .so

CC = `curl-config --cc`
CFLAGS += `curl-config --cflags`

.c.so:
	$(CC) $(CFLAGS) $(CPPFLAGS) $(LDFLAGS) -shared -fPIC \
		-Wl,-soname,$@ -o $@ $<

show-targets:
	ls *c |sed -e 's/.c$$/.so/' | awk '{print $$1 " \\"}'
