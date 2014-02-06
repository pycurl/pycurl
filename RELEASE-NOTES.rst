Release Notes
=============

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
