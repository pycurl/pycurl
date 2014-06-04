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
    c.setopt(c.WRITEFUNCTION, buffer.write)
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

Python 3 version is slightly more complicated::

    import pycurl
    from io import BytesIO

    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(c.URL, 'http://pycurl.sourceforge.net/')
    c.setopt(c.WRITEFUNCTION, buffer.write)
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
