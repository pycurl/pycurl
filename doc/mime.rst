.. _mime:

Mime Objects
============

PycURL exposes libcurl's MIME tree API via ``Mime`` and ``MimePart`` classes.

``Mime`` offers both low-level wrappers and higher-level builder helpers:

- Low-level: ``addpart()`` and ``MimePart`` methods such as ``name()``,
  ``data()``, ``data_cb()``, ``filedata()`` and ``subparts()``.
- Builder helpers: ``add()``, ``add_field()``, ``add_file()`` and
  ``add_multipart()``.
- ``MimePart.data()`` also accepts objects exposing Python's buffer protocol
  (for example ``bytearray`` and ``memoryview``), not only ``bytes``/ASCII ``str``.
- ``MimePart.data_cb(datasize, read, seek=None, free=None, userdata=None)`` maps to libcurl
  ``curl_mime_data_cb()`` for streaming content from callbacks.
  ``read(userdata, max_bytes)`` uses the same return conventions as ``READFUNCTION``.
  Optional ``seek(userdata, offset, origin)`` follows ``SEEKFUNCTION`` semantics and
  should return ``SEEKFUNC_OK``, ``SEEKFUNC_FAIL`` or ``SEEKFUNC_CANTSEEK``.
  Optional ``free(userdata)`` is called when libcurl releases the callback-backed part.

Example::

    import pycurl

    curl = pycurl.Curl()
    mime = pycurl.Mime(curl)

    mime.add_field("field1", "value1")
    mime.add_file("upload", "/tmp/example.txt", content_type="text/plain")

    nested = mime.add_multipart(name="attachments", subtype="mixed")
    nested.add_field("meta", "nested-value")

.. note::

    This is a first-draft API. It currently documents MIME object construction
    and nesting. End-to-end request attachment via Curl options is documented
    separately as that integration is finalized.

.. note::

    Ownership and handle constraints:

    - ``Mime`` objects passed to ``Curl.setopt(pycurl.MIMEPOST, mime)`` must be
      top-level/owning MIME trees (not already attached via ``subparts()``).
    - ``MimePart.subparts(child)`` requires both ``Mime`` objects to use the
      same ``Curl`` handle.
    - A ``Mime`` currently set as ``MIMEPOST`` cannot be attached as ``subparts()``.
    - ``Curl.duphandle()`` duplicates callback-backed MIME parts and shares the
      callback ``userdata`` pointer between handles, matching libcurl behavior.


Mime
----

.. autoclass:: pycurl.Mime

    Mime objects have the following methods:

    .. automethod:: pycurl.Mime.close

    .. automethod:: pycurl.Mime.closed

    .. automethod:: pycurl.Mime.addpart

    .. automethod:: pycurl.Mime.add

    .. automethod:: pycurl.Mime.add_field

    .. automethod:: pycurl.Mime.add_file

    .. automethod:: pycurl.Mime.add_multipart


MimePart
--------

.. autoclass:: pycurl.MimePart

    MimePart objects have the following methods:

    .. automethod:: pycurl.MimePart.name

    .. automethod:: pycurl.MimePart.data

    .. automethod:: pycurl.MimePart.data_cb

    .. automethod:: pycurl.MimePart.filedata

    .. automethod:: pycurl.MimePart.filename

    .. automethod:: pycurl.MimePart.type

    .. automethod:: pycurl.MimePart.encoder

    .. automethod:: pycurl.MimePart.headers

    .. automethod:: pycurl.MimePart.subparts
