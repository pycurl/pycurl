CC=gcc
RM=rm
CP=cp
PYINCLUDE=/usr/include/python1.5
CURLINCLUDE=/usr/include/curl
INCLUDE=-I$(PYINCLUDE) -I$(CURLINCLUDE)
LIBS=-L/usr/lib -lcurl
LDOPTS=-shared
CCOPTS=-g -O2 -Wall -Wstrict-prototypes -fPIC

all:
	$(CC) $(INCLUDE) $(CCOPTS) -c curl.c -o curl.o
	$(CC) $(LIBS) $(LDOPTS) -lcurl curl.o -o pycurlmodule.so

install: all
	$(CP) pycurlmodule.so /usr/lib/python1.5/site-packages

clean:
	$(RM) -f *~ *.o *.so
