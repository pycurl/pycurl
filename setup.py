#! /usr/bin/env python

# $Id$

"""Setup script for the PycURL module distribution."""

import os, sys
from distutils.core import setup
from distutils.extension import Extension
from string import strip, split

include_dirs = []
define_macros = []
library_dirs = []
libraries = []
runtime_library_dirs = []
extra_objects = []
extra_link_args = []

if sys.platform == "win32":
    # Windows users have to configure the CURL_DIR path parameter to match
    # their cURL source installation.  The path set here is just an example
    # and thus unlikely to match your installation.
    CURL_DIR = r"c:\src\curl-7.9.8"
    include_dirs.append(os.path.join(CURL_DIR, "include"))
    extra_objects.append(os.path.join(CURL_DIR, "lib", "libcurl.lib"))
else:
    # Find out the rest the hard way
    cflags = split(strip(os.popen("curl-config --cflags").read()), " ")
    for e in cflags[:]:
        if e[:2] == "-I":
            include_dirs.append(e[2:])
    libs = split(strip(os.popen("curl-config --libs").read()), " ")
    for e in libs[:]:
        if e[:2] == "-L":
            library_dirs.append(e[2:])
    libraries = ["curl"]

    # Add extra compile flag for MacOS X
    if sys.platform[:-1] == "darwin":
        extra_link_args.append("-flat_namespace")


###############################################################################

setup (name="pycurl",
       version="7.9.9",
       description="PycURL -- cURL library module for Python",
       author="Kjetil Jacobsen",
       author_email="kjetilja@cs.uit.no",
       url="http://pycurl.sourceforge.net/",
       data_files = [(os.path.join('doc', 'pycurl'),
                    ['README', 'COPYING', 'INSTALL', 'TODO'])],
       ext_modules=[Extension(name="pycurl",
                              sources=[os.path.join("src", "curl.c")],
                              include_dirs=include_dirs,
                              define_macros=define_macros,
                              library_dirs=library_dirs,
                              libraries=libraries,
                              runtime_library_dirs=runtime_library_dirs,
                              extra_objects=extra_objects,
                              extra_link_args=extra_link_args)]
        )
