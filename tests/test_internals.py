#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id$

#
# a simple self-test
#

try:
    # need Python 2.2 or better for garbage collection
    from gc import get_objects
    import gc
    del get_objects
    gc.enable()
except ImportError:
    gc = None
import copy, os, sys
from StringIO import StringIO
try:
    import cPickle
except ImportError:
    cPickle = None
try:
    import pickle
except ImportError:
    pickle = None

# update sys.path when running in the build directory
from util import get_sys_path
sys.path = get_sys_path()

import pycurl
from pycurl import Curl, CurlMulti


class opts:
    verbose = 1

if "-q" in sys.argv:
    opts.verbose = opts.verbose - 1


print "Python", sys.version
print "PycURL %s (compiled against 0x%x)" % (pycurl.version, pycurl.COMPILE_LIBCURL_VERSION_NUM)
print "PycURL version info", pycurl.version_info()
print "  %s, compiled %s" % (pycurl.__file__, pycurl.COMPILE_DATE)


# /***********************************************************************
# // test misc
# ************************************************************************/

if 1:
    c = Curl()
    assert c.URL is pycurl.URL
    del c


# /***********************************************************************
# // test handles
# ************************************************************************/

# remove an invalid handle: this should fail
if 1:
    m = CurlMulti()
    c = Curl()
    try:
        m.remove_handle(c)
    except pycurl.error:
        pass
    else:
        assert 0, "internal error"
    del m, c


# remove an invalid but closed handle
if 1:
    m = CurlMulti()
    c = Curl()
    c.close()
    m.remove_handle(c)
    del m, c


# add a closed handle: this should fail
if 1:
    m = CurlMulti()
    c = Curl()
    c.close()
    try:
        m.add_handle(c)
    except pycurl.error:
        pass
    else:
        assert 0, "internal error"
    m.close()
    del m, c


# add a handle twice: this should fail
if 1:
    m = CurlMulti()
    c = Curl()
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
    m1 = CurlMulti()
    m2 = CurlMulti()
    c = Curl()
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
    m1 = CurlMulti()
    m2 = CurlMulti()
    c = Curl()
    m1.add_handle(c)
    m1.remove_handle(c)
    m2.add_handle(c)
    del m1, m2, c


# /***********************************************************************
# // test copying and pickling - copying and pickling of
# // instances of Curl and CurlMulti is not allowed
# ************************************************************************/

if 1 and copy:
    c = Curl()
    m = CurlMulti()
    try:
        copy.copy(c)
    except copy.Error:
        pass
    else:
        assert 0, "internal error - copying should fail"
    try:
        copy.copy(m)
    except copy.Error:
        pass
    else:
        assert 0, "internal error - copying should fail"

if 1 and pickle:
    c = Curl()
    m = CurlMulti()
    fp = StringIO()
    p = pickle.Pickler(fp, 1)
    try:
        p.dump(c)
    except pickle.PicklingError:
        pass
    else:
        assert 0, "internal error - pickling should fail"
    try:
        p.dump(m)
    except pickle.PicklingError:
        pass
    else:
        assert 0, "internal error - pickling should fail"
    del c, m, fp, p

if 1 and cPickle:
    c = Curl()
    m = CurlMulti()
    fp = StringIO()
    p = cPickle.Pickler(fp, 1)
    try:
        p.dump(c)
    except cPickle.PicklingError:
        pass
    else:
        assert 0, "internal error - pickling should fail"
    try:
        p.dump(m)
    except cPickle.PicklingError:
        pass
    else:
        assert 0, "internal error - pickling should fail"
    del c, m, fp, p


# /***********************************************************************
# // test refcounts
# ************************************************************************/

# basic check of reference counting (use a memory checker like valgrind)
if 1:
    c = Curl()
    m = CurlMulti()
    m.add_handle(c)
    del m
    m = CurlMulti()
    c.close()
    del m, c

# basic check of cyclic garbage collection
if 1 and gc:
    gc.collect()
    c = Curl()
    c.m = CurlMulti()
    c.m.add_handle(c)
    # create some nasty cyclic references
    c.c = c
    c.c.c1 = c
    c.c.c2 = c
    c.c.c3 = c.c
    c.c.c4 = c.m
    c.m.c = c
    c.m.m = c.m
    c.m.c = c
    # delete
    gc.collect()
    flags = gc.DEBUG_COLLECTABLE | gc.DEBUG_UNCOLLECTABLE | gc.DEBUG_OBJECTS
    if opts.verbose >= 1:
        flags = flags | gc.DEBUG_STATS
    gc.set_debug(flags)
    gc.collect()
    ##print gc.get_referrers(c)
    ##print gc.get_objects()
    if opts.verbose >= 1:
        print "Tracked objects:", len(gc.get_objects())
    # The `del' below should delete these 4 objects:
    #   Curl + internal dict, CurlMulti + internal dict
    del c
    gc.collect()
    if opts.verbose >= 1:
        print "Tracked objects:", len(gc.get_objects())


# /***********************************************************************
# // done
# ************************************************************************/

print "All tests passed."
