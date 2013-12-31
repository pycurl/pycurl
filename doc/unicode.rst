Unicode
=======

Python 2.x
----------

Under Python 2, (binary) string and Unicode types are interchangeable.
PycURL will pass whatever strings it is given verbatim to libcurl.
When dealing with Unicode data, this typically means things like
HTTP request bodies should be encoded to utf-8 before passing them to PycURL.
Similarly it is on the application to decode HTTP response bodies, if
they are expected to contain non-ASCII characters.

Python 3.x (from PycURL 7.19.3 onward)
--------------------------------------

Under Python 3, the rules are as follows:

PycURL will accept bytes for any string data passed to libcurl (e.g.
arguments to curl_easy_setopt).

PycURL will accept (Unicode) strings for string arguments to curl_easy_setopt.
libcurl generally expects the options to be already appropriately encoded
and escaped (e.g. for CURLOPT_URL). Also, Python 2 code dealing with
Unicode values for string options will typically manually encode such values.
Therefore PycURL will attempt to encode Unicode strings with the ascii codec
only, allowing the application to pass ASCII data in a straightforward manner
but requiring Unicode data to be appropriately encoded.

It may be helpful to remember that libcurl operates on byte arrays.
It is a C library and does not do any Unicode encoding or decoding, offloading
that task on the application using it. PycURL, being a thin wrapper around
libcurl, passes the Unicode encoding and decoding responsibilities to you
except for the trivial case of encoding Unicode data containing only ASCII
characters into ASCII.

Caution: when using CURLOPT_READFUNCTION in tandem with CURLOPT_POSTFIELDSIZE,
as would be done for HTTP for example, take care to pass the length of
encoded data to CURLOPT_POSTFIELDSIZE if you are doing the encoding from
Unicode strings. If you pass the number of Unicode characters rather than
encoded bytes to libcurl, the server will receive wrong Content-Length.
Alternatively you can return Unicode strings from a CURLOPT_READFUNCTION
function, if you are certain they will only contain ASCII code points.

If encoding to ASCII fails, PycURL will return an error to libcurl, and
libcurl in turn will fail the request with an exception like
"read function error/data error". You may examine sys.last_value for
information on exception that occurred during encoding in this case.

PycURL will return all data read from the network as bytes. In particular,
this means that BytesIO should be used rather than StringIO for writing the
response to memory. Header function will also receive bytes.

Because PycURL does not perform encoding or decoding, other than to ASCII,
any file objects that PycURL is meant to interact with via CURLOPT_READDATA,
CURLOPT_WRITEDATA, CURLOPT_WRITEHEADER, CURLOPT_READFUNCTION,
CURLOPT_WRITEFUNCTION or CURLOPT_HEADERFUNCTION must be opened in binary
mode ("b" flag to open() call).

Python 3.x before PycURL 7.19.3
-------------------------------

PycURL did not have official Python 3 support prior to PycURL 7.19.3.
There were two patches on SourceForge (original_, revised_)
adding Python 3 support, but they did not handle Unicode strings correctly.
Instead of using Python encoding functionality, these patches used
C standard library unicode to multibyte conversion functions, and thus
they can have the same behavior as Python encoding code or behave
entirely differently.

Python 3 support as implemented in PycURL 7.19.3 and documented here
does not, as mentioned, actually perform any encoding other than to convert
from Unicode strings containing ASCII-only bytes to ASCII byte strings.

Linux distributions that offered Python 3 packages of PycURL prior to 7.19.3
used SourceForge patches and may behave in ways contradictory to what is
described in this document.

.. _original: http://sourceforge.net/p/pycurl/patches/5/
.. _revised: http://sourceforge.net/p/pycurl/patches/12/
