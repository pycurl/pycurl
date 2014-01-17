``PycURL`` -- A Python Interface To The cURL library
====================================================

The pycurl package is a Python interface to `libcurl`_.
pycurl has been successfully built and
tested with Python versions from 2.4 to 2.7 and 3.1 to 3.3.

libcurl is a client-side URL transfer library supporting FTP, FTPS, HTTP,
HTTPS, GOPHER, TELNET, DICT, FILE and LDAP. libcurl also supports HTTPS
certificates, HTTP POST, HTTP PUT, FTP uploads, proxies, cookies, basic
authentication, file transfer resume of FTP sessions, HTTP proxy tunneling
and more.

All the functionality provided by libcurl can used through the pycurl
interface. The following subsections describe how to use the pycurl
interface, and assume familiarity with how libcurl works. For information on
how libcurl works, please consult the `curl library C API`_.

Module Functionality
--------------------

**pycurl.global_init**\ (*option*) -> *None*

*option* is one of the constants pycurl.GLOBAL_SSL, pycurl.GLOBAL_WIN32,
pycurl.GLOBAL_ALL, pycurl.GLOBAL_NOTHING, pycurl.GLOBAL_DEFAULT. Corresponds
to `curl_global_init`_ in libcurl.

**pycurl.global_cleanup**\ () -> *None*

Corresponds to `curl_global_cleanup`_ in libcurl.

**pycurl.version**

This is a string with version information on libcurl, corresponding to
`curl_version`_ in libcurl.

Example usage:

::

    >>> import pycurl
    >>> pycurl.version
    'PycURL/7.19.3 libcurl/7.33.0 OpenSSL/0.9.8x zlib/1.2.7'

**pycurl.version_info**\ () -> *Tuple*

Corresponds to `curl_version_info`_ in libcurl. Returns a tuple of
information which is similar to the ``curl_version_info_data`` struct
returned by ``curl_version_info()`` in libcurl.

Example usage:

::

    >>> import pycurl
    >>> pycurl.version_info()
    (3, '7.33.0', 467200, 'amd64-portbld-freebsd9.1', 33436, 'OpenSSL/0.9.8x',
    0, '1.2.7', ('dict', 'file', 'ftp', 'ftps', 'gopher', 'http', 'https',
    'imap', 'imaps', 'pop3', 'pop3s', 'rtsp', 'smtp', 'smtps', 'telnet',
    'tftp'), None, 0, None)

**pycurl.Curl**\ () -> *Curl object*

This function creates a new `Curl object`_ which corresponds to a ``CURL``
handle in libcurl. Curl objects automatically set CURLOPT_VERBOSE to 0,
CURLOPT_NOPROGRESS to 1, provide a default CURLOPT_USERAGENT and setup
CURLOPT_ERRORBUFFER to point to a private error buffer.

**pycurl.CurlMulti**\ () -> *CurlMulti object*

This function creates a new `CurlMulti object`_ which corresponds to a
``CURLM`` handle in libcurl.

**pycurl.CurlShare**\ () -> *CurlShare object*

This function creates a new `CurlShare object`_ which corresponds to a
``CURLSH`` handle in libcurl. CurlShare objects is what you pass as an
argument to the SHARE option on Curl objects.


Subsections
-----------

-   `Curl objects`_
-   `CurlMulti objects`_
-   `CurlShare objects`_
-   `Callbacks`_
-   `Unicode handling`_
-   `File handling`_


Documentation For Developers
============================

-   `Notes on PycURL internals`_
-   `Release process`_

.. _libcurl: http://curl.haxx.se/libcurl/
.. _curl library C API: http://curl.haxx.se/libcurl/c/
.. _curl_global_init: http://curl.haxx.se/libcurl/c/curl_global_init.html
.. _curl_global_cleanup: http://curl.haxx.se/libcurl/c/curl_global_cleanup.html
.. _curl_version: http://curl.haxx.se/libcurl/c/curl_version.html
.. _curl_version_info: http://curl.haxx.se/libcurl/c/curl_version_info.html
.. _Curl object: curlobject.html
.. _Curl objects: curlobject.html
.. _CurlMulti object: curlmultiobject.html
.. _CurlMulti objects: curlmultiobject.html
.. _CurlShare object: curlshareobject.html
.. _CurlShare objects: curlshareobject.html
.. _Callbacks: callbacks.html
.. _Unicode handling: unicode.html
.. _File handling: files.html
.. _Notes on PycURL internals: internals.html
.. _Release process: release-process.html
