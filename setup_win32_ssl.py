#! /usr/bin/env python
# vi:ts=4:et

# $Id$

import os, sys, string
assert sys.platform == "win32"


CURL_DIR = r"c:\src\build\curl-7.10.1-ssl"
OPENSSL_DIR = r"c:\src\build\openssl-0.9.6g"
ZLIB_DIR = r"c:\src\build\zlib-1.1.4"
sys.argv.insert(1, "--curl-dir=" + CURL_DIR)

from setup import *

setup_args["name"] = "pycurl-ssl"


ext.extra_objects.append(os.path.join(OPENSSL_DIR, "out32", "RSAglue.lib"))
ext.extra_objects.append(os.path.join(OPENSSL_DIR, "out32", "libeay32.lib"))
ext.extra_objects.append(os.path.join(OPENSSL_DIR, "out32", "ssleay32.lib"))
if 0:
    ext.extra_objects.append(os.path.join(ZLIB_DIR, "zlib114.lib"))
else:
    ext.extra_link_args.append("zlib114.lib")
ext.extra_link_args.append("ws2_32.lib")
ext.extra_link_args.append("winmm.lib")
ext.extra_link_args.append("gdi32.lib")


if __name__ == "__main__":
    for o in ext.extra_objects:
        assert os.path.isfile(o), o
    apply(setup, (), setup_args)

