# $Id$
# vi:ts=4:et

import pycurl
print "Testing", pycurl.version
print pycurl.__file__, pycurl.__COMPILE_DATE__


#####
##### self-test assertion section
#####


# remove an invalid handle: this should fail
if 1:
    m = pycurl.multi_init()
    c = pycurl.init()
    try:
        m.remove_handle(c)
    except pycurl.error:
        pass
    else:
        assert 0, "internal error"
    del m, c


# remove an invalid but closed handle
if 1:
    m = pycurl.multi_init()
    c = pycurl.init()
    c.cleanup()
    m.remove_handle(c)
    del m, c


# add a closed handle: this should fail
if 1:
    m = pycurl.multi_init()
    c = pycurl.init()
    c.cleanup()
    try:
        m.add_handle(c)
    except pycurl.error:
        pass
    else:
        assert 0, "internal error"
    m.cleanup()
    del m, c


# add a handle twice: this should fail
if 1:
    m = pycurl.multi_init()
    c = pycurl.init()
    m.add_handle(c)
    try:
        m.add_handle(c)
    except pycurl.error:
        pass
    else:
        assert 0, "internal error"
    del m, c


# add a handle on multiple stacks: this should fail
if 1:
    m1 = pycurl.multi_init()
    m2 = pycurl.multi_init()
    c = pycurl.init()
    m1.add_handle(c)
    try:
        m2.add_handle(c)
    except pycurl.error:
        pass
    else:
        assert 0, "internal error"
    del m1, m2, c


# move a handle
if 1:
    m1 = pycurl.multi_init()
    m2 = pycurl.multi_init()
    c = pycurl.init()
    m1.add_handle(c)
    m1.remove_handle(c)
    m2.add_handle(c)
    del m1, m2, c


# basic check of reference counting (use a memory checker like valgrind)
if 1:
    c = pycurl.init()
    m = pycurl.multi_init()
    m.add_handle(c)
    del m
    m = pycurl.multi_init()
    c.cleanup()
    del m, c


print "All tests passed."
