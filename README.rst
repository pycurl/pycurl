PycURL: Python interface to libcurl
====================================

.. image:: https://api.travis-ci.org/pycurl/pycurl.png
	   :target: https://travis-ci.org/pycurl/pycurl

PycURL is a Python interface to `libcurl`_. PycURL can be used to fetch objects
identified by a URL from a Python program, similar to the `urllib`_ Python module.
PycURL is mature, very fast, and supports a lot of features.

Overview
--------

- libcurl is a free and easy-to-use client-side URL transfer library, supporting
  FTP, FTPS, HTTP, HTTPS, SCP, SFTP, TFTP, TELNET, DICT, LDAP, LDAPS, FILE, IMAP,
  SMTP, POP3 and RTSP. libcurl supports SSL certificates, HTTP POST, HTTP PUT,
  FTP uploading, HTTP form based upload, proxies, cookies, user+password
  authentication  (Basic, Digest, NTLM, Negotiate, Kerberos4), file transfer
  resume, http proxy tunneling and more!

- libcurl is highly portable, it builds and works identically on numerous
  platforms, including Solaris, NetBSD, FreeBSD, OpenBSD, Darwin, HPUX, IRIX,
  AIX, Tru64, Linux, UnixWare, HURD, Windows, Amiga, OS/2, BeOs, Mac OS X,
  Ultrix, QNX, OpenVMS, RISC OS, Novell NetWare, DOS and more...

- libcurl is `free`_, `thread-safe`_, `IPv6 compatible`_, `feature rich`_,
  `well supported`_, `fast`_, `thoroughly documented`_ and is already used by
  many known, big and successful `companies`_ and numerous `applications`_.

.. _free: http://curl.haxx.se/docs/copyright.html
.. _thread-safe: http://curl.haxx.se/libcurl/features.html#thread
.. _`IPv6 compatible`: http://curl.haxx.se/libcurl/features.html#ipv6
.. _`feature rich`: http://curl.haxx.se/libcurl/features.html#features
.. _`well supported`: http://curl.haxx.se/libcurl/features.html#support
.. _`fast`: http://curl.haxx.se/libcurl/features.html#fast
.. _`thoroughly documented`: http://curl.haxx.se/libcurl/features.html#docs
.. _companies: http://curl.haxx.se/docs/companies.html
.. _applications: http://curl.haxx.se/libcurl/using/apps.html

Requirements
------------

- Python 2.4 through 2.7 or 3.1 through 3.3.
- libcurl 7.19.0 or better.

Installation
------------

You can install the most recent PycURL version using `easy_install`_::

    easy_install pycurl

or `pip`_::

    pip install pycurl

Installing from source is performed via ``setup.py``::

    python setup.py install

You will need libcurl headers and libraries installed to install PycURL
from source. PycURL uses ``curl-config`` to determine correct flags/libraries
to use during compilation; you can override the location of ``curl-config``
if it is not in PATH or you want to use a custom libcurl installation::

    python setup.py --curl-config=/path/to/curl-config install

Sometimes it is more convenient to use an environment variable, if
you are not directly invoking ``setup.py``::

    PYCURL_CURL_CONFIG=/path/to/curl-config python setup.py install

``curl-config`` is expected to support the following options:

- ``--version``
- ``--cflags``
- ``--libs``
- ``--static-libs`` (if ``--libs`` does not work)

PycURL requires that the SSL library that it is built against is the same
one libcurl, and therefore PycURL, uses at runtime. PycURL's ``setup.py``
uses ``curl-config`` to attempt to figure out which SSL library libcurl
was compiled against, however this does not always work. If PycURL is unable
to determine the SSL library in use it will print a warning similar to
the following:

    src/pycurl.c:137:4: warning: #warning "libcurl was compiled with SSL support, but configure could not determine which " "library was used; thus no SSL crypto locking callbacks will be set, which may " "cause random crashes on SSL requests" [-Wcpp]

It will then fail at runtime as follows:

    ImportError: pycurl: libcurl link-time ssl backend (openssl) is different from compile-time ssl backend (none/other)

To fix this, you need to tell ``setup.py`` what SSL backend is used:

    python setup.py --with-[ssl|gnutls|nss] install

Or use an environment variable:

    PYCURL_SSL_LIBRARY=openssl|gnutls|nss python setup.py installl

Note the difference between ``--with-ssl`` (for compatibility with libcurl) and
``PYCURL_SSL_LIBRARY=openssl``.

.. _easy_install: http://peak.telecommunity.com/DevCenter/EasyInstall
.. _pip: http://pypi.python.org/pypi/pip

Automated Tests
---------------

PycURL comes with an automated test suite. To run the tests, execute::

    make test

The suite depends on packages `nose`_, `bottle`_ and `cherrypy`_.

Some tests use vsftpd configured to accept anonymous uploads. These tests
are not run by default. As configured, vsftpd will allow reads and writes to
anything the user running the tests has read and write access. To run
vsftpd tests you must explicitly set PYCURL_VSFTPD_PATH variable like so::

    # use vsftpd in PATH
    export PYCURL_VSFTPD_PATH=vsftpd

    # specify full path to vsftpd
    export PYCURL_VSFTPD_PATH=/usr/local/libexec/vsftpd

These instructions work for Python 2.5 through 2.7 and 3.1 through 3.3.

.. _nose: https://nose.readthedocs.org/
.. _bottle: http://bottlepy.org/
.. _cherrypy: http://www.cherrypy.org/

Test Matrix
-----------

The test matrix is a separate framework that runs tests on more esoteric
configurations. It supports:

- Testing against Python 2.4, which bottle does not support.
- Testing against Python compiled without threads, which requires an out of
  process test server.
- Testing against locally compiled libcurl with arbitrary options.

To use the test matrix, first you need to start the test server from
Python 2.5+ by running:::

    python -m tests.appmanager

Then in a different shell, and preferably in a separate user account,
run the test matrix:::

    # run ftp tests, etc.
    export PYCURL_VSFTPD_PATH=vsftpd
    # create a new work directory, preferably not under pycurl tree
    mkdir testmatrix
    cd testmatrix
    # run the matrix specifying absolute path
    python /path/to/pycurl/tests/matrix.py

The test matrix will download, build and install supported Python versions
and supported libcurl versions, then run pycurl tests against each combination.
To see what the combinations are, look in
`tests/matrix.py <tests/matrix.py>`_.

Contribute
----------

For smaller changes:

#. Fork `the repository`_ on Github.
#. Create a branch off **master**.
#. Make your changes.
#. Write a test which shows that the bug was fixed or that the feature
   works as expected.
#. Send a pull request.

For larger changes:

#. Join the `mailing list`_.
#. Discuss your proposal on the mailing list.
#. When consensus is reached, implement it as described above.

Please contribute binary distributions for your system to the
`downloads repository`_.

License
-------

::

    Copyright (C) 2001-2008 by Kjetil Jacobsen <kjetilja at gmail.com>
    Copyright (C) 2001-2008 by Markus F.X.J. Oberhumer <markus at oberhumer.com>
    Copyright (C) 2013 by Oleg Pudeyev <oleg at bsdpower.com>

    All rights reserved.

    PycURL is dual licensed under the LGPL and an MIT/X derivative license
    based on the cURL license.  A full copy of the LGPL license is included
    in the file COPYING-LGPL.  A full copy of the MIT/X derivative license is
    included in the file COPYING-MIT.  You can redistribute and/or modify PycURL
    according to the terms of either license.

.. _PycURL: http://pycurl.sourceforge.net/
.. _libcurl: http://curl.haxx.se/libcurl/
.. _urllib: http://docs.python.org/library/urllib.html
.. _`the repository`: https://github.com/pycurl/pycurl
.. _`mailing list`: http://cool.haxx.se/mailman/listinfo/curl-and-python
.. _`downloads repository`: https://github.com/pycurl/downloads
