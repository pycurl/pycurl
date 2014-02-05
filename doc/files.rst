File Handling
=============

In PycURL 7.19.0.3 and below, CURLOPT_READDATA, CURLOPT_WRITEDATA and
CURLOPT_WRITEHEADER options accepted file objects and directly passed
the underlying C library FILE pointers to libcurl.

Python 3 no longer implements files as C library FILE objects.
In PycURL 7.19.3 and above, when running on Python 3, these options
are implemented as calls to CURLOPT_READFUNCTION, CURLOPT_WRITEFUNCTION
and CURLOPT_HEADERFUNCTION, respectively, with the write method of the
Python file object as the parameter. As a result, any Python file-like
object implementing a write method can be passed to CURLOPT_READDATA,
CURLOPT_WRITEDATA or CURLOPT_WRITEHEADER options.

When running PycURL 7.19.3 and above on Python 2, the old behavior of
passing FILE pointers to libcurl remains when a true file object is given
to CURLOPT_READDATA, CURLOPT_WRITEDATA and CURLOPT_WRITEHEADER options.
For consistency with Python 3 behavior these options also accept file-like
objects implementing a write method as arguments, in which case the
Python 3 code path is used converting these options to CURLOPT_*FUNCTION
option calls.

Files given to PycURL as arguments to CURLOPT_READDATA, CURLOPT_WRITEDATA or
CURLOPT_WRITEHEADER must be opened for writing in binary mode. Files opened
in text mode (without "b" flag to open()) expect string objects and writing
to them from PycURL will fail. Similarly when passing f.write method of
an open file to CURLOPT_WRITEFUNCTION or CURLOPT_HEADERFUNCTION, or f.read
to CURLOPT_READFUNCTION, the file must have been be opened in binary mode.
