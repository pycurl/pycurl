PycURL Quick Start
==================

Retrieving A Network Resource
-----------------------------

Once PycURL is installed we can perform network operations. The simplest
one is retrieving a resource by its URL. Here is how to do it in Python 2::

    import pycurl
    from StringIO import StringIO

    buffer = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, 'http://pycurl.sourceforge.net/')
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()

    body = buffer.getvalue()
    # Body is a string in some encoding.
    # In Python 2, we can print it without knowing what the encoding is.
    print(body)

This code is available as ``examples/quickstart/get_python2.py``.

PycURL does not provide storage for the network response - that is the
application's job. Therefore we must setup a buffer (in the form of a
StringIO object) and instruct PycURL to write to that buffer.

Most of the existing PycURL code uses WRITEFUNCTION instead of WRITEDATA
as follows::

    c.setopt(c.WRITEFUNCTION, buffer.write)

While the WRITEFUNCTION idiom continues to work, it is now unnecessary.
As of PycURL 7.19.3 WRITEDATA accepts any Python object with a ``write``
method.

Python 3 version is slightly more complicated::

    import pycurl
    from io import BytesIO

    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, 'http://pycurl.sourceforge.net/')
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()

    body = buffer.getvalue()
    # Body is a byte string.
    # We have to know the encoding in order to print it to a text file
    # such as standard output.
    print(body.decode('iso-8859-1'))

This code is available as ``examples/quickstart/get_python3.py``.

In Python 3, PycURL response the response body as a byte string.
This is handy if we are downloading a binary file, but for text documents
we must decode the byte string. In the above example, we assume that the
body is encoded in iso-8859-1.

Python 2 and Python 3 versions can be combined. Doing so requires decoding
the response body as in Python 3 version. The code for the combined
example can be found in ``examples/quickstart/get.py``.

Examining Response Headers
--------------------------

In reality we want to decode the response using the encoding specified by
the server rather than assuming an encoding. To do this we need to
examine the response headers::

    import pycurl
    import re
    try:
        from io import BytesIO
    except ImportError:
        from StringIO import StringIO as BytesIO

    headers = {}
    def header_function(header_line):
        # HTTP standard specifies that headers are encoded in iso-8859-1.
        # On Python 2, decoding step can be skipped.
        # On Python 3, decoding step is required.
        header_line = header_line.decode('iso-8859-1')
        
        # Header lines include the first status line (HTTP/1.x ...).
        # We are going to ignore all lines that don't have a colon in them.
        # This will botch headers that are split on multiple lines...
        if ':' not in header_line:
            return
        
        # Break the header line into header name and value.
        name, value = header_line.split(':', 1)
        
        # Remove whitespace that may be present.
        # Header lines include the trailing newline, and there may be whitespace
        # around the colon.
        name = name.strip()
        value = value.strip()
        
        # Header names are case insensitive.
        # Lowercase name here.
        name = name.lower()
        
        # Now we can actually record the header name and value.
        headers[name] = value

    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, 'http://pycurl.sourceforge.net')
    c.setopt(c.WRITEFUNCTION, buffer.write)
    # Set our header function.
    c.setopt(c.HEADERFUNCTION, header_function)
    c.perform()
    c.close()

    # Figure out what encoding was sent with the response, if any.
    # Check against lowercased header name.
    encoding = None
    if 'content-type' in headers:
        content_type = headers['content-type'].lower()
        match = re.search('charset=(\S+)', content_type)
        if match:
            encoding = match.group(1)
            print('Decoding using %s' % encoding)
    if encoding is None:
        # Default encoding for HTML is iso-8859-1.
        # Other content types may have different default encoding,
        # or in case of binary data, may have no encoding at all.
        encoding = 'iso-8859-1'
        print('Assuming encoding is %s' % encoding)

    body = buffer.getvalue()
    # Decode using the encoding we figured out.
    print(body.decode(encoding))

This code is available as ``examples/quickstart/response_headers.py``.

That was a lot of code for something very straightforward. Unfortunately,
as libcurl refrains from allocating memory for response data, it is on our
application to perform this grunt work.

Writing To A File
-----------------

Suppose we want to save response body to a file. This is actually easy
for a change::

    import pycurl

    # As long as the file is opened in binary mode, both Python 2 and Python 3
    # can write response body to it without decoding.
    with open('out.html', 'wb') as f:
        c = pycurl.Curl()
        c.setopt(c.URL, 'http://pycurl.sourceforge.net/')
        c.setopt(c.WRITEDATA, f)
        c.perform()
        c.close()

This code is available as ``examples/quickstart/write_file.py``.

The important part is opening the file in binary mode - then response body
can be written bytewise without decoding or encoding steps.

Following Redirects
-------------------

By default libcurl, and PycURL, do not follow redirects. Changing this
behavior involves using ``setopt`` like so::

    import pycurl

    c = pycurl.Curl()
    # Redirects to https://www.python.org/.
    c.setopt(c.URL, 'http://www.python.org/')
    # Follow redirect.
    c.setopt(c.FOLLOWLOCATION, True)
    c.perform()
    c.close()

This code is available as ``examples/quickstart/follow_redirect.py``.

As we did not set a write callback, the default libcurl and PycURL behavior
to write response body to standard output takes effect.

Setting Options
---------------

Following redirects is one option that libcurl provides. There are many more
such options, and they are documented on `curl_easy_setopt`_ page.
With very few exceptions, PycURL option names are derived from libcurl
option names by removing the ``CURLOPT_`` prefix. Thus, ``CURLOPT_URL``
becomes simply ``URL``.

.. _curl_easy_setopt: http://curl.haxx.se/libcurl/c/curl_easy_setopt.html
