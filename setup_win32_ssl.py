#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id$

import os, sys, string
assert sys.platform == "win32", "Only for building on Win32 with SSL and zlib"


CURL_DIR = r"c:\src\build\pycurl\curl-7.19.0-ssl"
OPENSSL_DIR = r"c:\src\build\pycurl\openssl-0.9.7g"
sys.argv.insert(1, "--curl-dir=" + CURL_DIR)

from setup import *

setup_args["name"] = "pycurl-ssl"

for l in ("libeay32.lib", "ssleay32.lib",):
    ext.extra_objects.append(os.path.join(OPENSSL_DIR, "out32", l))

define_macros.append(('HAVE_CURL_SSL', 1))
define_macros.append(('HAVE_CURL_OPENSSL', 1))

pool = "\\" + r"pool\win32\vc6" + "\\"
if string.find(sys.version, "MSC v.1310") >= 0:
    pool = "\\" + r"pool\win32\vc71" + "\\"
ext.extra_objects.append(r"c:\src\pool\zlib-1.2.2" + pool + "zlib.lib")
ext.extra_objects.append(r"c:\src\pool\c-ares-20050411" + pool + "ares.lib")
ext.extra_objects.append(r"c:\src\pool\libidn-0.5.15" + pool + "idn.lib")


if __name__ == "__main__":
    for o in ext.extra_objects:
        assert os.path.isfile(o), o
    apply(setup, (), setup_args)

