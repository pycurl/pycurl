Callbacks
=========

For more fine-grained control, libcurl allows a number of callbacks to be
associated with each connection. In pycurl, callbacks are defined using the
``setopt()`` method for Curl objects with options WRITEFUNCTION,
READFUNCTION, HEADERFUNCTION, PROGRESSFUNCTION, IOCTLFUNCTION, or
DEBUGFUNCTION. These options correspond to the libcurl options with CURLOPT_*
prefix removed. A callback in pycurl must be either a regular Python
function, a class method or an extension type function.

There are some limitations to some of the options which can be used
concurrently with the pycurl callbacks compared to the libcurl callbacks.
This is to allow different callback functions to be associated with different
Curl objects. More specifically, WRITEDATA cannot be used with WRITEFUNCTION,
READDATA cannot be used with READFUNCTION, WRITEHEADER cannot be used with
HEADERFUNCTION, PROGRESSDATA cannot be used with PROGRESSFUNCTION, IOCTLDATA
cannot be used with IOCTLFUNCTION, and DEBUGDATA cannot be used with
DEBUGFUNCTION. In practice, these limitations can be overcome by having a
callback function be a class instance method and rather use the class
instance attributes to store per object data such as files used in the
callbacks.

The signature of each callback used in pycurl is as follows:

**WRITEFUNCTION**\ (*string*) -> *number of characters written*

**READFUNCTION**\ (*number of characters to read*) -> *string*

**HEADERFUNCTION**\ (*string*) -> *number of characters written*

**PROGRESSFUNCTION**\ (*download total, downloaded, upload total,
uploaded*) -> *status*

**DEBUGFUNCTION**\ (*debug message type, debug message string*) -> *None*

**IOCTLFUNCTION**\ (*ioctl cmd*) -> *status*

In addition, ``READFUNCTION`` may return ``READFUNC_ABORT`` or
``READFUNC_PAUSE``. See the libcurl documentation for an explanation of these
values. The ``WRITEFUNCTION`` and ``HEADERFUNCTION`` callbacks may return
``None``, which is an alternate way of indicating that the callback has
consumed all of the string passed to it.

Example: Callbacks for document header and body
-----------------------------------------------

This example prints the header data to stderr and the body data to stdout.
Also note that neither callback returns the number of bytes written. For
WRITEFUNCTION and HEADERFUNCTION callbacks, returning None implies that all
bytes where written.

::

    ## Callback function invoked when body data is ready
    def body(buf):
        # Print body data to stdout
        import sys
        sys.stdout.write(buf)
        # Returning None implies that all bytes were written

    ## Callback function invoked when header data is ready
    def header(buf):
        # Print header data to stderr
        import sys
        sys.stderr.write(buf)
        # Returning None implies that all bytes were written

    c = pycurl.Curl()
    c.setopt(pycurl.URL, "http://www.python.org/")
    c.setopt(pycurl.WRITEFUNCTION, body)
    c.setopt(pycurl.HEADERFUNCTION, header)
    c.perform()

Example: Download/upload progress callback
------------------------------------------

This example shows how to use the progress callback. When downloading a
document, the arguments related to uploads are zero, and vice versa.

::

    ## Callback function invoked when download/upload has
    progress
    def progress(download_t, download_d, upload_t, upload_d):
        print "Total to download", download_t
        print "Total downloaded", download_d
        print "Total to upload", upload_t
        print "Total uploaded", upload_d

    c.setopt(c.URL, "http://slashdot.org/")
    c.setopt(c.NOPROGRESS, 0)
    c.setopt(c.PROGRESSFUNCTION, progress)
    c.perform()

Example: Debug callbacks
------------------------

This example shows how to use the debug callback. The debug message type is
an integer indicating the type of debug message. The VERBOSE option must be
enabled for this callback to be invoked.

::

    def test(debug_type, debug_msg):
        print "debug(%d): %s" % (debug_type, debug_msg)

    c = pycurl.Curl()
    c.setopt(pycurl.URL, "http://curl.haxx.se/")
    c.setopt(pycurl.VERBOSE, 1)
    c.setopt(pycurl.DEBUGFUNCTION, test)
    c.perform()

Other examples
--------------

The pycurl distribution also contains a number of test scripts and examples
which show how to use the various callbacks in libcurl. For instance, the
file 'examples/file_upload.py' in the distribution contains example code for
using READFUNCTION, 'tests/test_cb.py' shows WRITEFUNCTION and
HEADERFUNCTION, 'tests/test_debug.py' shows DEBUGFUNCTION, and
'tests/test_getinfo.py' shows PROGRESSFUNCTION.
