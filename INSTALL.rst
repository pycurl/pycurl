PycURL Installation
===================

NOTE: You need Python and libcurl installed on your system to use or
build pycurl.  Some RPM distributions of curl/libcurl do not include
everything necessary to build pycurl, in which case you need to
install the developer specific RPM which is usually called curl-dev.


Distutils
---------

Build and install pycurl with the following commands::

    (if necessary, become root)
    tar -zxvf pycurl-$VER.tar.gz
    cd pycurl-$VER
    python setup.py install

$VER should be substituted with the pycurl version number, e.g. 7.10.5.

Note that the installation script assumes that 'curl-config' can be
located in your path setting.  If curl-config is installed outside
your path or you want to force installation to use a particular
version of curl-config, use the '--curl-config' command line option to
specify the location of curl-config.  Example::

    python setup.py install --curl-config=/usr/local/bin/curl-config

If libcurl is linked dynamically with pycurl, you may have to alter the
LD_LIBRARY_PATH environment variable accordingly.  This normally
applies only if there is more than one version of libcurl installed,
e.g. one in /usr/lib and one in /usr/local/lib.


easy_install / pip
------------------

::

    easy_install pycurl
    pip install pycurl

If you need to specify an alternate curl-config, it can be done via an
environment variable::

    export PYCURL_CURL_CONFIG=/usr/local/bin/curl-config
    easy_install pycurl

The same applies to the SSL backend, if you need to specify it (see the SSL
section below)::

    export PYCURL_SSL_LIBRARY=openssl
    easy_install pycurl


SSL
---

PycURL has locks around crypto functions. In order to compile correct locking
code, it has to know which SSL library is going to be used by libcurl at
runtime. setup.py will attempt to automatically detect the SSL library that
libcurl uses, but this does not always work. In the cases when setup.py cannot
figure out the SSL library, it must be provided via --with-ssl/--with-gnutls/
--with-nss arguments, just like libcurl's configure script uses, or via
PYCURL_SSL_LIBRARY=openssl|gnutls|nss environment variable.

Please note the difference in spelling that concerns OpenSSL: the command-line
argument is --with-ssl, to match libcurl, but the environment variable value is
"openssl".


Windows
-------

First, you will need to obtain dependencies. These can be precompiled binaries
or source packages that you are going to compile yourself.

For a minimum build you will just need libcurl source. Follow its Windows
build instructions to build either a static or a DLL version of the library,
then configure PycURL as follows to use it::

    python setup.py --curl-dir=c:\dev\curl-7.33.0\builds\libcurl-vc-x86-release-dll-ipv6-sspi-spnego-winssl --use-libcurl-dll

Note that ``--curl-dir`` does not point to libcurl source but rather to headers
and compiled libraries.

Additional Windows setup.py options:

- ``--use-libcurl-dll`` - build against libcurl DLL, if not given PycURL will
  be built against libcurl statically.
- ``--libcurl-lib-name=libcurl_imp.lib`` - specify a different name for libcurl
  import library. The default is ``libcurl.lib`` which is appropriate for
  static linking and is sometimes the correct choice for dynamic linking as
  well. The other possibility for dynamic linking is ``libcurl_imp.lib``.

A good ``setup.py`` target to use is ``bdist_wininst`` which produces an
executable installer that you can run to install PycURL.
