.. _unicode:

String And Unicode Handling
===========================

Generally speaking, libcurl does not perform data encoding or decoding.
In particular, libcurl is not Unicode-aware, but operates on byte streams.
libcurl leaves it up to the application - PycURL library or an application
using PycURL in this case - to encode and decode Unicode data into byte streams.

PycURL, being a thin wrapper around libcurl, generally does not perform
this encoding and decoding either, leaving it up to the application.
Specifically:

- Data that PycURL passes to an application, such as via callback functions,
  is normally byte strings. The application must decode them to obtain text
  (Unicode) data.
- Data that an application passes to PycURL, such as via ``setopt`` calls,
  must normally be byte strings appropriately encoded. For convenience and
  compatibility with existing code, PycURL will accept Unicode strings that
  contain ASCII code points only [#ascii]_, and transparently encode these to
  byte strings.


Setting Options - Python 2.x
----------------------------

Under Python 2, the ``str`` type can hold arbitrary encoded byte strings.
PycURL will pass whatever byte strings it is given verbatim to libcurl.
The following code will work::

    >>> import pycurl
    >>> c = pycurl.Curl()
    >>> c.setopt(c.USERAGENT, 'Foo\xa9')
    # ok

Unicode strings can be used but must contain ASCII code points only::

    >>> c.setopt(c.USERAGENT, u'Foo')
    # ok

    >>> c.setopt(c.USERAGENT, u'Foo\xa9')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    UnicodeEncodeError: 'ascii' codec can't encode character u'\xa9' in position 3: ordinal not in range(128)

    >>> c.setopt(c.USERAGENT, u'Foo\xa9'.encode('iso-8859-1'))
    # ok


Setting Options - Python 3.x
----------------------------

Under Python 3, the ``bytes`` type holds arbitrary encoded byte strings.
PycURL will accept ``bytes`` values for all options where libcurl specifies
a "string" argument::

    >>> import pycurl
    >>> c = pycurl.Curl()
    >>> c.setopt(c.USERAGENT, b'Foo\xa9')
    # ok

The ``str`` type holds Unicode data. PycURL will accept ``str`` values
containing ASCII code points only::

    >>> c.setopt(c.USERAGENT, 'Foo')
    # ok

    >>> c.setopt(c.USERAGENT, 'Foo\xa9')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    UnicodeEncodeError: 'ascii' codec can't encode character '\xa9' in position 3: ordinal not in range(128)

    >>> c.setopt(c.USERAGENT, 'Foo\xa9'.encode('iso-8859-1'))
    # ok


Writing To Files
----------------

PycURL will return all data read from the network as byte strings. On Python 2,
this means the write callbacks will receive ``str`` objects, and
on Python 3, write callbacks will receive ``bytes`` objects.

Under Python 2, when using e.g. ``WRITEDATA`` or ``WRITEFUNCTION`` options,
files being written to *should* be opened in binary mode. Writing to files
opened in text mode will not raise exceptions but may corrupt data.

Under Python 3, PycURL passes strings and binary data to the application
using ``bytes`` instances. When writing to files, the files must be opened
in binary mode for the writes to work::

    import pycurl
    c = pycurl.Curl()
    c.setopt(c.URL,'http://pycurl.sourceforge.net')
    # File opened in binary mode.
    with open('/dev/null','wb') as f:
        c.setopt(c.WRITEDATA, f)
        # Same result if using WRITEFUNCTION instead:
        #c.setopt(c.WRITEFUNCTION, f.write)
        c.perform()
    # ok

If a file is opened in text mode (``w`` instead of ``wb`` mode), an error
similar to the following will result::

    TypeError: must be str, not bytes
    Traceback (most recent call last):
      File "/tmp/test.py", line 8, in <module>
        c.perform()
    pycurl.error: (23, 'Failed writing body (0 != 168)')

The TypeError is actually an exception raised by Python which will be printed,
but not propagated, by PycURL. PycURL will raise a ``pycurl.error`` to
signify operation failure.


Writing To StringIO/BytesIO
---------------------------

Under Python 2, response can be saved in memory by using a ``StringIO``
object::

    import pycurl
    from StringIO import StringIO
    c = pycurl.Curl()
    c.setopt(c.URL,'http://pycurl.sourceforge.net')
    buffer = StringIO()
    c.setopt(c.WRITEDATA, buffer)
    # Same result if using WRITEFUNCTION instead:
    #c.setopt(c.WRITEFUNCTION, buffer.write)
    c.perform()
    # ok

Under Python 3, as PycURL invokes the write callback with ``bytes`` argument,
the response must be written to a ``BytesIO`` object::

    import pycurl
    from io import BytesIO
    c = pycurl.Curl()
    c.setopt(c.URL,'http://pycurl.sourceforge.net')
    buffer = BytesIO()
    c.setopt(c.WRITEDATA, buffer)
    # Same result if using WRITEFUNCTION instead:
    #c.setopt(c.WRITEFUNCTION, buffer.write)
    c.perform()
    # ok

Attempting to use a ``StringIO`` object will produce an error::

    import pycurl
    from io import StringIO
    c = pycurl.Curl()
    c.setopt(c.URL,'http://pycurl.sourceforge.net')
    buffer = StringIO()
    c.setopt(c.WRITEDATA, buffer)
    c.perform()

    TypeError: string argument expected, got 'bytes'
    Traceback (most recent call last):
      File "/tmp/test.py", line 9, in <module>
        c.perform()
    pycurl.error: (23, 'Failed writing body (0 != 168)')

The following idiom can be used for code that needs to be compatible with both
Python 2 and Python 3::

    import pycurl
    try:
        # Python 3
        from io import BytesIO
    except ImportError:
        # Python 2
        from StringIO import StringIO as BytesIO
    c = pycurl.Curl()
    c.setopt(c.URL,'http://pycurl.sourceforge.net')
    buffer = BytesIO()
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    # ok
    # Decode the response body:
    string_body = buffer.getvalue().decode('utf-8')


Header Functions
----------------

Although headers are often ASCII text, they are still returned as
``bytes`` instances on Python 3 and thus require appropriate decoding.
HTTP headers are encoded in ISO/IEC 8859-1 according to the standards.

When using ``WRITEHEADER`` option to write headers to files, the files
should be opened in binary mode in Python 2 and must be opened in binary
mode in Python 3, same as with ``WRITEDATA``.


Read Functions
--------------

Read functions are expected to provide data in the same fashion as
string options expect it:

- On Python 2, the data can be given as ``str`` instances, appropriately
  encoded.
- On Python 2, the data can be given as ``unicode`` instances containing
  ASCII code points only.
- On Python 3, the data can be given as ``bytes`` instances.
- On Python 3. the data can be given as ``str`` instances containing
  ASCII code points only.

Caution: when using CURLOPT_READFUNCTION in tandem with CURLOPT_POSTFIELDSIZE,
as would be done for HTTP for example, take care to pass the length of
*encoded* data to CURLOPT_POSTFIELDSIZE if you are performing the encoding.
If you pass the number of Unicode characters rather than
encoded bytes to libcurl, the server will receive wrong Content-Length.
Alternatively you can return Unicode strings from a CURLOPT_READFUNCTION
function, if your data contains only ASCII code points,
and let PycURL encode them for you.


How PycURL Handles Unicode Strings
----------------------------------

If PycURL is given a Unicode string which contains non-ASCII code points,
and as such cannot be encoded to ASCII,PycURL will return an error to libcurl,
and libcurl in turn will fail the request with an error like
"read function error/data error". PycURL will then raise ``pycurl.error``
with this latter message. The encoding exception that was the
underlying cause of the problem is stored as ``sys.last_value``.


Figuring Out Correct Encoding
-----------------------------

What encoding should be used when is a complicated question. For example,
when working with HTTP:

- URLs and POSTFIELDS data must be URL-encoded. A URL-encoded string has
  only ASCII code points.
- Headers must be ISO/IEC 8859-1 encoded.
- Encoding for bodies is specified in Content-Type and Content-Encoding headers.


Legacy PycURL Versions
----------------------

The Unicode handling documented here was implemented in PycURL 7.19.3
along with Python 3 support. Prior to PycURL 7.19.3 Unicode data was not
accepted at all::

    >>> import pycurl
    >>> c = pycurl.Curl()
    >>> c.setopt(c.USERAGENT, u'Foo\xa9')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    TypeError: invalid arguments to setopt

Some GNU/Linux distributions provided Python 3 packages of PycURL prior to
PycURL 7.19.3. These packages included unofficial patches
([#patch1]_, [#patch2]_) which did not handle Unicode correctly, and did not behave
as described in this document. Such unofficial versions of PycURL should
be avoided.


.. rubric:: Footnotes

.. [#ascii] Only ASCII is accepted; ISO-8859-1/Latin 1, for example, will be
    rejected.
.. [#patch1] http://sourceforge.net/p/pycurl/patches/5/
.. [#patch2] http://sourceforge.net/p/pycurl/patches/12/
