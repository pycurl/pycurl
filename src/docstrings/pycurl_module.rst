This module implements an interface to the cURL library.

Types:

Curl() -> New object.  Create a new curl object.
CurlMulti() -> New object.  Create a new curl multi object.
CurlShare() -> New object.  Create a new curl share object.

Functions:

global_init(option) -> None.  Initialize curl environment.
global_cleanup() -> None.  Cleanup curl environment.
version_info() -> tuple.  Return version information.
