Unicode
=======

Under Python 2, (binary) string and Unicode types are interchangeable.
PycURL will pass whatever strings it is given verbatim to libcurl.
When dealing with Unicode data, this typically means things like
HTTP request bodies should be encoded to utf-8 before passing them to PycURL.
Similarly it is on the application to decode HTTP response bodies, if
they are expected to contain non-ASCII characters.

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

Caution: when using CURLOPT_READFUNCTION in tandem with CURLOPT_POSTFIELDSIZE,
as would be done for HTTP for example, take care to pass the length of
encoded data to CURLOPT_POSTFIELDSIZE. You can return Unicode strings from
a CURLOPT_READFUNCTION function, but as stated above they will only be
encoded to ASCII.

If encoding to ASCII fails, libcurl will fail the request with something
like a "read function/data error". You may examine sys.last_value for
information on exception that occurred during encoding in this case.

PycURL will return all data read from the network as bytes. In particular,
this means that BytesIO should be used rather than StringIO for writing the
response to memory. Header function will also receive bytes.

Because PycURL does not perform encoding or decoding, other than to ASCII,
any file objects that PycURL is meant to interact with via CURLOPT_READDATA,
CURLOPT_WRITEDATA, CURLOPT_WRITEHEADER, CURLOPT_READFUNCTION,
CURLOPT_WRITEFUNCTION or CURLOPT_HEADERFUNCTION must be opened in binary
mode ("b" flag to open() call).
