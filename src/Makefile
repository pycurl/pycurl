CC=gcc
RM=rm
CP=cp
PYINCLUDE=/usr/include/python2.2
CURLINCLUDE=/usr/include/curl
INCLUDE=-I$(PYINCLUDE) -I$(CURLINCLUDE)
LIBS=-L/usr/lib -lcurl
LDOPTS=-shared
CCOPTS=-g -O2 -Wall -Wstrict-prototypes -fPIC

all:
	$(CC) $(INCLUDE) $(CCOPTS) -c pycurl.c -o pycurl.o
	$(CC) $(LIBS) $(LDOPTS) -lcurl pycurl.o -o pycurl.so

install: all
	$(CP) pycurl.so /usr/lib/python2.2/site-packages

clean:
	$(RM) -f *~ *.o *obj *.so
