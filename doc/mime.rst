.. _mime:

CurlMime Objects
================

PycURL exposes libcurl's MIME tree API via ``CurlMime`` and ``CurlMimePart`` classes.

``CurlMime`` offers both low-level wrappers and higher-level builder helpers:

- Low-level: ``addpart()`` and ``CurlMimePart`` methods such as ``name()``,
  ``data()``, ``data_cb()``, ``filedata()`` and ``subparts()``.
- Builder helpers: ``add()``, ``add_field()``, ``add_file()`` and
  ``add_multipart()``.
- ``CurlMimePart.data()`` also accepts objects exposing Python's buffer protocol
  (for example ``bytearray`` and ``memoryview``), not only ``bytes``/ASCII ``str``.
- ``CurlMimePart.data_cb()`` streams content from callbacks.

Example::

    import pycurl

    curl = pycurl.Curl()
    mime = pycurl.CurlMime(curl)

    mime.add_field("field1", "value1")
    mime.add_file("upload", "/tmp/example.txt", content_type="text/plain")

    nested = mime.add_multipart(name="attachments", subtype="mixed")
    nested.add_field("meta", "nested-value")

.. note::

    This is a first-draft API.

.. note::

    Ownership and handle constraints:

    - ``CurlMime`` objects passed to ``Curl.setopt(pycurl.MIMEPOST, mime)`` must be
      top-level/owning MIME trees (not already attached via ``subparts()``).
    - ``CurlMimePart.subparts(child)`` requires both ``CurlMime`` objects to use the
      same ``Curl`` handle.
    - A ``CurlMime`` currently set as ``MIMEPOST`` cannot be attached as ``subparts()``.
    - ``Curl.duphandle()`` duplicates callback-backed MIME parts and shares the
      callback ``userdata`` pointer between handles, matching libcurl behavior.


CurlMime
--------

.. autoclass:: pycurl.CurlMime

    CurlMime objects have the following methods:

    .. automethod:: pycurl.CurlMime.close

    .. autoattribute:: pycurl.CurlMime.closed

    .. automethod:: pycurl.CurlMime.addpart

    .. automethod:: pycurl.CurlMime.add

    .. automethod:: pycurl.CurlMime.add_field

    .. automethod:: pycurl.CurlMime.add_file

    .. automethod:: pycurl.CurlMime.add_multipart


CurlMimePart
------------

.. autoclass:: pycurl.CurlMimePart

    CurlMimePart objects have the following methods:

    .. automethod:: pycurl.CurlMimePart.name

    .. automethod:: pycurl.CurlMimePart.data

    .. automethod:: pycurl.CurlMimePart.data_cb

    .. automethod:: pycurl.CurlMimePart.filedata

    .. automethod:: pycurl.CurlMimePart.filename

    .. automethod:: pycurl.CurlMimePart.type

    .. automethod:: pycurl.CurlMimePart.encoder

    .. automethod:: pycurl.CurlMimePart.headers

    .. automethod:: pycurl.CurlMimePart.subparts

