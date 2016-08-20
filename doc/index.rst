PycURL -- A Python Interface To The cURL library
================================================

PycURL is a Python interface to `libcurl`_, the multiprotocol file
transfer library. Similarly to the urllib_ Python module,
PycURL can be used to fetch objects identified by a URL from a Python program.
Beyond simple fetches however PycURL exposes most of the functionality of
libcurl, including:

- Speed - libcurl is very fast and PycURL, being a thin wrapper above
  libcurl, is very fast as well. PycURL `was benchmarked`_ to be several
  times faster than requests_.
- Features including multiple protocol support, SSL, authentication and
  proxy options. PycURL supports most of libcurl's callbacks.
- Multi_ and share_ interfaces.
- Sockets used for network operations, permitting integration of PycURL
  into the application's I/O loop (e.g., using Tornado_).

.. _was benchmarked: http://stackoverflow.com/questions/15461995/python-requests-vs-pycurl-performance
.. _requests: http://python-requests.org/
.. _Multi: https://curl.haxx.se/libcurl/c/libcurl-multi.html
.. _share: https://curl.haxx.se/libcurl/c/libcurl-share.html
.. _Tornado: http://www.tornadoweb.org/


About libcurl
-------------

- libcurl is a free and easy-to-use client-side URL transfer library, supporting
  DICT, FILE, FTP, FTPS, Gopher, HTTP, HTTPS, IMAP, IMAPS, LDAP, LDAPS, POP3,
  POP3S, RTMP, RTSP, SCP, SFTP, SMTP, SMTPS, Telnet and TFTP.
  libcurl supports SSL certificates, HTTP POST, HTTP PUT,
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

.. _free: https://curl.haxx.se/docs/copyright.html
.. _thread-safe: https://curl.haxx.se/libcurl/features.html#thread
.. _`IPv6 compatible`: https://curl.haxx.se/libcurl/features.html#ipv6
.. _`feature rich`: https://curl.haxx.se/libcurl/features.html#features
.. _`well supported`: https://curl.haxx.se/libcurl/features.html#support
.. _`fast`: https://curl.haxx.se/libcurl/features.html#fast
.. _`thoroughly documented`: https://curl.haxx.se/libcurl/features.html#docs
.. _companies: https://curl.haxx.se/docs/companies.html
.. _applications: https://curl.haxx.se/libcurl/using/apps.html


Requirements
------------

- Python 2.6, 2.7 or 3.1 through 3.5.
- libcurl 7.19.0 or better.


Installation
------------

On Unix, PycURL is easiest to install using your operating system's package
manager. This will also install libcurl and other dependencies as needed.

Installation via easy_install and pip is also supported::

    easy_install pycurl
    pip install pycurl

If this does not work, please see :ref:`install`.

On Windows, use pip to install a binary wheel for Python 2.6, 2.7 or
3.2 through 3.5::

    pip install pycurl

If not using pip, binary distributions in other formats are available
`on Bintray`_.

.. _on Bintray: https://dl.bintray.com/pycurl/pycurl/


Support
-------

For support questions, please use `curl-and-python mailing list`_.
`Mailing list archives`_ are available for your perusal as well.

Although not an official support venue, `Stack Overflow`_ has been
popular with PycURL users as well.

Bugs can be reported `via GitHub`_. Please only use GitHub issues when you are
certain you have found a bug in PycURL. If you do not have a patch to fix
the bug, or at least a specific code fragment in PycURL that you believe is
the cause, you should instead post your inquiry to the mailing list.

.. _curl-and-python mailing list: http://cool.haxx.se/mailman/listinfo/curl-and-python
.. _Stack Overflow: http://stackoverflow.com/questions/tagged/pycurl
.. _Mailing list archives: https://curl.haxx.se/mail/list.cgi?list=curl-and-python
.. _via GitHub: https://github.com/pycurl/pycurl/issues


Documentation Contents
----------------------

.. toctree::
   :maxdepth: 2

   release-notes
   install
   quickstart
   pycurl
   curlobject
   curlmultiobject
   curlshareobject
   callbacks
   curl
   unicode
   files
   unimplemented


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _libcurl: https://curl.haxx.se/libcurl/
.. _urllib: http://docs.python.org/library/urllib.html
