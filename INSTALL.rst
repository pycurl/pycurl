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

PycURL requires that the SSL library that it is built against is the same
one libcurl, and therefore PycURL, uses at runtime. PycURL's ``setup.py``
uses ``curl-config`` to attempt to figure out which SSL library libcurl
was compiled against, however this does not always work. If PycURL is unable
to determine the SSL library in use it will print a warning similar to
the following::

    src/pycurl.c:137:4: warning: #warning "libcurl was compiled with SSL support, but configure could not determine which " "library was used; thus no SSL crypto locking callbacks will be set, which may " "cause random crashes on SSL requests" [-Wcpp]

It will then fail at runtime as follows::

    ImportError: pycurl: libcurl link-time ssl backend (openssl) is different from compile-time ssl backend (none/other)

To fix this, you need to tell ``setup.py`` what SSL backend is used::

    python setup.py --with-[ssl|gnutls|nss] install


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
note above)::

    export PYCURL_SSL_LIBRARY=[openssl|gnutls|nss]
    easy_install pycurl

Please note the difference in spelling that concerns OpenSSL: the command-line
argument is --with-ssl, to match libcurl, but the environment variable value is
"openssl".


Windows
-------

Binary Packages
...............

Binary packages are available in the `download area`_
for some Windows and Python version combinations.
Currently, 32-bit packages are available for Python 2.6, 2.7, 3.2 and 3.3.
64-bit packages are not presently available.

In order to use the official binary packages, your installation of Python must
have been compiled against the same MS Visual C++ runtime that the packages
have been compiled against. Importantly, which version of MSVC is used
has changed in minor releases of Python, for example between 2.7.3 and 2.7.6.
As such, you may need to upgrade or downgrade your version of Python to use
official PycURL packages.

Currently official PycURL packages are built against the following Python
versions:

- 2.6.6
- 2.7.6
- 3.2.5
- 3.3.5

If CRTs used by PycURL and Python do not match, you will receive a message
like following when trying to import pycurl module::

    ImportError: DLL load failed: The specified procedure could not be found.

To troubleshoot this situation use the `application profiling feature`_ of
`Dependency Walker`_ and look for `msvcrt.dll variants`_ being loaded.
You may find `the entire thread starting here`_ helpful.

.. _application profiling feature: http://curl.haxx.se/mail/curlpython-2014-05/0007.html
.. _Dependency Walker: http://www.dependencywalker.com/
.. _msvcrt.dll variants: http://curl.haxx.se/mail/curlpython-2014-05/0010.html
.. _the entire thread starting here: http://curl.haxx.se/mail/curlpython-2014-05/0000.html

Installing From Source
......................

First, you will need to obtain dependencies. These can be precompiled binaries
or source packages that you are going to compile yourself.

For a minimum build you will just need libcurl source. Follow its Windows
build instructions to build either a static or a DLL version of the library,
then configure PycURL as follows to use it::

    python setup.py --curl-dir=c:\dev\curl-7.33.0\builds\libcurl-vc-x86-release-dll-ipv6-sspi-spnego-winssl --use-libcurl-dll

Note that ``--curl-dir`` does not point to libcurl source but rather to headers
and compiled libraries.

If libcurl and Python are not linked against the same exact C runtime
(version number, static/dll, single-threaded/multi-threaded) you must use
``--avoid-stdio`` option (see below).

Additional Windows setup.py options:

- ``--use-libcurl-dll``: build against libcurl DLL, if not given PycURL will
  be built against libcurl statically.
- ``--libcurl-lib-name=libcurl_imp.lib``: specify a different name for libcurl
  import library. The default is ``libcurl.lib`` which is appropriate for
  static linking and is sometimes the correct choice for dynamic linking as
  well. The other possibility for dynamic linking is ``libcurl_imp.lib``.
- ``--avoid-stdio``: on windows, a process and each library it is using
  may be linked to its own version of the C runtime (msvcrt).
  FILE pointers from one C runtime may not be passed to another C runtime.
  This option prevents direct passing of FILE pointers from Python to libcurl,
  thus permitting Python and libcurl to be linked against different C runtimes.
  This option may carry a performance penalty when Python file objects are
  given directly to PycURL in CURLOPT_READDATA, CURLOPT_WRITEDATA or
  CURLOPT_WRITEHEADER options. This option applies only on Python 2; on
  Python 3, file objects no longer expose C library FILE pointers and the
  C runtime issue does not exist. On Python 3, this option is recognized but
  does nothing. You can also give ``--avoid-stdio`` option in
  PYCURL_SETUP_OPTIONS environment variable as follows::

    PYCURL_SETUP_OPTIONS=--avoid-stdio pip install pycurl

A good ``setup.py`` target to use is ``bdist_wininst`` which produces an
executable installer that you can run to install PycURL.

You may find the following mailing list posts helpful:

- http://curl.haxx.se/mail/curlpython-2009-11/0010.html
- http://curl.haxx.se/mail/curlpython-2013-11/0002.html


winbuild.py
...........

This script is used to build official PycURL Windows packages. You can
use it to build a full complement of packages with your own options or modify
it to build a single package you need.

Prerequisites:

- msysgit_.
- Appropriate `Python versions`_ installed.
- MS Visual C++ 9/2008 for Python <= 3.2, MS Visual C++ 10/2010 for
  Python >= 3.3. Express versions of Visual Studio work fine for this.

.. _msysgit: http://msysgit.github.io/
.. _Python versions: http://python.org/download/

``winbuild.py`` assumes all programs are installed in their default locations,
if this is not the case edit it as needed. ``winbuild.py`` itself can be run
with any Python it supports - 2.6, 2.7, 3.2, 3.3 or 3.4.

.. _`download area`: http://pycurl.sourceforge.net/download/


Git Checkout
------------

In order to build PycURL from a Git checkout, some files need to be
generated. On Unix systems it is easiest to build PycURL with ``make``::

    make

To specify which curl or SSL backend to compile against, use the same
environment variables as easy_install/pip, namely ``PYCURL_CURL_CONFIG``
and ``PYCURL_SSL_LIBRARY``.

To generate generated files only you may run::

    make gen

This might be handy if you are on Windows. Remember to run ``make gen``
whenever you change sources.

To generate documentation, run::

    make docs

Generating documentation requires `Sphinx`_ to be installed.

.. _Sphinx: http://sphinx-doc.org/
