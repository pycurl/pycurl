Release Notes
=============

PycURL 7.19.5.1 - 2015-01-06
----------------------------

This release primarily fixes build breakage against libcurl 7.19.4 through
7.21.1, such as versions shipped with CentOS.


PycURL 7.19.5 - 2014-07-12
--------------------------

PycURL C code has been significantly reorganized. Curl, CurlMulti and
CurlShare classes are now properly exported, instead of factory functions for
the respective objects. PycURL API has not changed.

Documentation has been transitioned to Sphinx and reorganized as well.
Both docstrings and standalone documentation are now more informative.

Documentation is no longer included in released distributions. It can be
generated from source by running `make docs`.

Tests are no longer included in released distributions. Instead the
documentation and quickstart examples should be consulted for sample code.

Official Windows builds now are linked against zlib.


PycURL 7.19.3.1 - 2014-02-05
----------------------------

This release restores PycURL's ability to automatically detect SSL library
in use in most circumstances, thanks to Andjelko Horvat.


PycURL 7.19.3 - 2014-01-09
--------------------------

This release brings official Python 3 support to PycURL.
Several GNU/Linux distributions provided Python 3 packages of PycURL
previously; these packages were based on patches that were incomplete and
in some places incorrect. Behavior of PycURL 7.19.3 and later may therefore
differ from behavior of unofficial Python 3 packages of previous PycURL
versions.

To summarize the behavior under Python 3, PycURL will accept ``bytes`` where
it accepted strings under Python 2, and will also accept Unicode strings
containing ASCII codepoints only for convenience. Please refer to
`Unicode`_ and `file`_ documentation for further details.

In the interests of compatibility, PycURL will also accept Unicode data on
Python 2 given the same constraints as under Python 3.

While Unicode and file handling rules are expected to be sensible for
all use cases, and retain backwards compatibility with previous PycURL
versions, please treat behavior of this versions under Python 3 as experimental
and subject to change.

Another potentially disruptive change in PycURL is the requirement for
compile time and runtime SSL backends to match. Please see the readme for
how to indicate the SSL backend to setup.py.

.. _Unicode: doc/unicode.html
.. _file: doc/files.html
