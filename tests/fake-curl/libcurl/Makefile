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
UNAME := $(shell uname -s)
ifeq ($(UNAME),Darwin)
	SONAME_FLAG = -install_name
else
	SONAME_FLAG = -soname
endif

.c.so:
	$(CC) $(CFLAGS) $(CPPFLAGS) $(LDFLAGS) -shared -fPIC \
		-Wl,$(SONAME_FLAG),$@ -o $@ $<

show-targets:
	ls *c |sed -e 's/.c$$/.so/' | awk '{print $$1 " \\"}'
