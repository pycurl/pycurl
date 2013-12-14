Internals
=========

Cleanup sequence:

x=curl/multi/share

x.close() -> do_x_close -> util_x_close
del x -> do_x_dealloc -> util_x_close

do_* functions are directly invoked by user code.
They check pycurl object state.

util_* functions are only invoked by other pycurl C functions.
They do not check pycurl object state.
