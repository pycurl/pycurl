#! /usr/bin/env python
# vi:ts=4:et

# $Id$

"""Setup script for the PycURL module distribution."""

import os, sys
import distutils
from distutils.core import setup
from distutils.extension import Extension
from distutils.util import split_quoted

include_dirs = []
define_macros = []
library_dirs = []
libraries = []
runtime_library_dirs = []
extra_objects = []
extra_compile_args = []
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
    cflags = split_quoted(os.popen("curl-config --cflags").read())
    for e in cflags[:]:
        if e[:2] == "-I":
            include_dirs.append(e[2:])
        else:
            extra_compile_args.append(e)
    libs = split_quoted(os.popen("curl-config --libs").read())
    for e in libs[:]:
        if e[:2] == "-l":
            libraries.append(e[2:])
        elif e[:2] == "-L":
            library_dirs.append(e[2:])
        else:
            extra_link_args.append(e)
    if not libraries:
        libraries = ["curl"]

    # Add extra compile flag for MacOS X
    if sys.platform[:-1] == "darwin":
        extra_link_args.append("-flat_namespace")


###############################################################################

def get_kw(**kw): return kw

ext = Extension(
    name="pycurl",
    sources=[
        os.path.join("src", "curl.c"),
    ],
    include_dirs=include_dirs,
    define_macros=define_macros,
    library_dirs=library_dirs,
    libraries=libraries,
    runtime_library_dirs=runtime_library_dirs,
    extra_objects=extra_objects,
    extra_compile_args=extra_compile_args,
    extra_link_args=extra_link_args,
)
##print ext.__dict__; sys.exit(1)

setup_args = get_kw(
    name="pycurl",
    version="7.9.8.3",
    description="PycURL -- cURL library module for Python",
    author="Kjetil Jacobsen, Markus F.X.J. Oberhumer",
    author_email="kjetilja@cs.uit.no, markus@oberhumer.com",
    maintainer="Kjetil Jacobsen, Markus F.X.J. Oberhumer",
    maintainer_email="kjetilja@cs.uit.no, markus@oberhumer.com",
    url="http://pycurl.sourceforge.net/",
    licence="GNU Lesser General Public License (LGPL)",
    data_files = [
        # tuple with path to install to and a list of files
        (os.path.join("doc", "pycurl"), ["README", "COPYING", "INSTALL", "TODO"]),
    ],
    ext_modules=[ext],
    long_description="""
This module provides Python bindings for the cURL library.""",
)

##print distutils.__version__
if distutils.__version__ >= "1.0.2":
    setup_args["platforms"] = "All"

apply(setup, (), setup_args)

