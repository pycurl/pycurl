PycURL Quick Start
==================

Retrieving A Network Resource
-----------------------------

Once PycURL is installed we can perform network operations. The simplest
one is retrieving a resource by its URL. To issue a network request with
PycURL, the following steps are required:

    1. Create a ``pycurl.Curl`` instance.
    2. Use ``setopt`` to set options.
    3. Call ``perform`` to perform the operation.

Here is how we can retrieve a network resource in Python 3::

    import pycurl
    import certifi
    from io import BytesIO

    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, 'http://pycurl.io/')
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(c.CAINFO, certifi.where())
    c.perform()
    c.close()

    body = buffer.getvalue()
    # Body is a byte string.
    # We have to know the encoding in order to print it to a text file
    # such as standard output.
    print(body.decode('iso-8859-1'))

This code is available as ``examples/quickstart/get_python3.py``.
For a Python 2 only example, see ``examples/quickstart/get_python2.py``.
For an example targeting Python 2 and 3, see ``examples/quickstart/get.py``.

PycURL does not provide storage for the network response - that is the
application's job. Therefore we must setup a buffer (in the form of a
StringIO object) and instruct PycURL to write to that buffer.

Most of the existing PycURL code uses WRITEFUNCTION instead of WRITEDATA
as follows::

    c.setopt(c.WRITEFUNCTION, buffer.write)

While the WRITEFUNCTION idiom continues to work, it is now unnecessary.
As of PycURL 7.19.3 WRITEDATA accepts any Python object with a ``write``
method.

Working With HTTPS
------------------

Most web sites today use HTTPS which is HTTP over TLS/SSL. In order to
take advantage of security that HTTPS provides, PycURL needs to utilize
a *certificate bundle*. As certificates change over time PycURL does not
provide such a bundle; one may be supplied by your operating system, but
if not, consider using the `certifi`_ Python package::

    import pycurl
    import certifi
    from io import BytesIO

    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, 'https://python.org/')
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(c.CAINFO, certifi.where())
    c.perform()
    c.close()

    body = buffer.getvalue()
    # Body is a byte string.
    # We have to know the encoding in order to print it to a text file
    # such as standard output.
    print(body.decode('iso-8859-1'))

This code is available as ``examples/quickstart/get_python3_https.py``.
For a Python 2 example, see ``examples/quickstart/get_python2_https.py``.


Troubleshooting
---------------

When things don't work as expected, use libcurl's ``VERBOSE`` option to
receive lots of debugging output pertaining to the request::

    c.setopt(c.VERBOSE, True)

It is often helpful to compare verbose output from the program using PycURL
with that of ``curl`` command line tool when the latter is invoked with
``-v`` option::

    curl -v http://pycurl.io/


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
        # Note: this only works when headers are not duplicated, see below.
        headers[name] = value

    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, 'http://pycurl.io')
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

One caveat with the above code is that if there are multiple headers
for the same name, such as Set-Cookie, only the last header value will be
stored. To record all values in multi-valued headers as a list the following
code can be used instead of ``headers[name] = value`` line::

    if name in headers:
        if isinstance(headers[name], list):
            headers[name].append(value)
        else:
            headers[name] = [headers[name], value]
    else:
        headers[name] = value


Writing To A File
-----------------

Suppose we want to save response body to a file. This is actually easy
for a change::

    import pycurl

    # As long as the file is opened in binary mode, both Python 2 and Python 3
    # can write response body to it without decoding.
    with open('out.html', 'wb') as f:
        c = pycurl.Curl()
        c.setopt(c.URL, 'http://pycurl.io/')
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

.. _curl_easy_setopt: https://curl.haxx.se/libcurl/c/curl_easy_setopt.html


Examining Response
------------------

We already covered examining response headers. Other response information is
accessible via ``getinfo`` call as follows::

    import pycurl
    try:
        from io import BytesIO
    except ImportError:
        from StringIO import StringIO as BytesIO

    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, 'http://pycurl.io/')
    c.setopt(c.WRITEDATA, buffer)
    c.perform()

    # HTTP response code, e.g. 200.
    print('Status: %d' % c.getinfo(c.RESPONSE_CODE))
    # Elapsed time for the transfer.
    print('Time: %f' % c.getinfo(c.TOTAL_TIME))

    # getinfo must be called before close.
    c.close()

This code is available as ``examples/quickstart/response_info.py``.

Here we write the body to a buffer to avoid printing uninteresting output
to standard out.

Response information that libcurl exposes is documented on
`curl_easy_getinfo`_ page. With very few exceptions, PycURL constants
are derived from libcurl constants by removing the ``CURLINFO_`` prefix.
Thus, ``CURLINFO_RESPONSE_CODE`` becomes simply ``RESPONSE_CODE``.

.. _curl_easy_getinfo: https://curl.haxx.se/libcurl/c/curl_easy_getinfo.html


Sending Form Data
-----------------

To send form data, use ``POSTFIELDS`` option. Form data must be URL-encoded
beforehand::

    import pycurl
    try:
        # python 3
        from urllib.parse import urlencode
    except ImportError:
        # python 2
        from urllib import urlencode

    c = pycurl.Curl()
    c.setopt(c.URL, 'https://httpbin.org/post')

    post_data = {'field': 'value'}
    # Form data must be provided already urlencoded.
    postfields = urlencode(post_data)
    # Sets request method to POST,
    # Content-Type header to application/x-www-form-urlencoded
    # and data to send in request body.
    c.setopt(c.POSTFIELDS, postfields)

    c.perform()
    c.close()

This code is available as ``examples/quickstart/form_post.py``.

``POSTFIELDS`` automatically sets HTTP request method to POST. Other request
methods can be specified via ``CUSTOMREQUEST`` option::

    c.setopt(c.CUSTOMREQUEST, 'PATCH')


File Upload - Multipart POST
----------------------------

To replicate the behavior of file upload in an HTML form (specifically,
a multipart form),
use ``HTTPPOST`` option. Such an upload is performed with a ``POST`` request.
See the next example for how to upload a file with a ``PUT`` request.

If the data to be uploaded is located in a physical file,
use ``FORM_FILE``::

    import pycurl

    c = pycurl.Curl()
    c.setopt(c.URL, 'https://httpbin.org/post')

    c.setopt(c.HTTPPOST, [
        ('fileupload', (
            # upload the contents of this file
            c.FORM_FILE, __file__,
        )),
    ])

    c.perform()
    c.close()

This code is available as ``examples/quickstart/file_upload_real.py``.

``libcurl`` provides a number of options to tweak file uploads and multipart
form submissions in general. These are documented on `curl_formadd page`_.
For example, to set a different filename and content type::

    import pycurl

    c = pycurl.Curl()
    c.setopt(c.URL, 'https://httpbin.org/post')

    c.setopt(c.HTTPPOST, [
        ('fileupload', (
            # upload the contents of this file
            c.FORM_FILE, __file__,
            # specify a different file name for the upload
            c.FORM_FILENAME, 'helloworld.py',
            # specify a different content type
            c.FORM_CONTENTTYPE, 'application/x-python',
        )),
    ])

    c.perform()
    c.close()

This code is available as ``examples/quickstart/file_upload_real_fancy.py``.

If the file data is in memory, use ``BUFFER``/``BUFFERPTR`` as follows::

    import pycurl

    c = pycurl.Curl()
    c.setopt(c.URL, 'https://httpbin.org/post')

    c.setopt(c.HTTPPOST, [
        ('fileupload', (
            c.FORM_BUFFER, 'readme.txt',
            c.FORM_BUFFERPTR, 'This is a fancy readme file',
        )),
    ])

    c.perform()
    c.close()

This code is available as ``examples/quickstart/file_upload_buffer.py``.


File Upload - PUT
-----------------

A file can also be uploaded in request body, via a ``PUT`` request.
Here is how this can be arranged with a physical file::

    import pycurl

    c = pycurl.Curl()
    c.setopt(c.URL, 'https://httpbin.org/put')

    c.setopt(c.UPLOAD, 1)
    file = open('body.json')
    c.setopt(c.READDATA, file)

    c.perform()
    c.close()
    # File must be kept open while Curl object is using it
    file.close()

This code is available as ``examples/quickstart/put_file.py``.

And if the data is stored in a buffer::

    import pycurl
    try:
        from io import BytesIO
    except ImportError:
        from StringIO import StringIO as BytesIO

    c = pycurl.Curl()
    c.setopt(c.URL, 'https://httpbin.org/put')

    c.setopt(c.UPLOAD, 1)
    data = '{"json":true}'
    # READDATA requires an IO-like object; a string is not accepted
    # encode() is necessary for Python 3
    buffer = BytesIO(data.encode('utf-8'))
    c.setopt(c.READDATA, buffer)

    c.perform()
    c.close()

This code is available as ``examples/quickstart/put_buffer.py``.

.. _curl_formadd page: https://curl.haxx.se/libcurl/c/curl_formadd.html
.. _certifi: https://pypi.org/project/certifi/
