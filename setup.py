#! /usr/bin/env python
# vi:ts=4:et

# $Id$

"""Setup script for the PycURL module distribution."""

VERSION = "7.10-pre4"

import os, sys, string
import distutils
from distutils.core import setup
from distutils.extension import Extension
from distutils.util import split_quoted
from distutils.version import LooseVersion

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
    args = sys.argv[:]
    for arg in args:
        if string.find(arg, '--curl-dir=') == 0:
            CURL_DIR = string.split(arg, '=')[1]
            sys.argv.remove(arg)
    print 'Using curl directory:', CURL_DIR
    include_dirs.append(os.path.join(CURL_DIR, "include"))
    extra_objects.append(os.path.join(CURL_DIR, "lib", "libcurl.lib"))
else:
    # Find out the rest the hard way
    args = sys.argv[:]
    CURL_CONFIG = 'curl-config'
    for arg in args:
        if string.find(arg, '--curl-config=') == 0:
            CURL_CONFIG = string.split(arg, '=')[1]
            sys.argv.remove(arg)
    d = os.popen("%s --version" % CURL_CONFIG).read()
    if not string.strip(d):
        raise Exception, "`curl-config' not found -- please install the libcurl development files"
    print 'Using %s (%s)' % (CURL_CONFIG, string.strip(d))
    for e in split_quoted(os.popen("%s --cflags" % CURL_CONFIG).read()):
        if e[:2] == "-I":
            include_dirs.append(e[2:])
        else:
            extra_compile_args.append(e)
    for e in split_quoted(os.popen("%s --libs" % CURL_CONFIG).read()):
        if e[:2] == "-l":
            libraries.append(e[2:])
        elif e[:2] == "-L":
            library_dirs.append(e[2:])
        else:
            extra_link_args.append(e)
    if not libraries:
        libraries.append("curl")
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
    version=VERSION,
    description="PycURL -- cURL library module for Python",
    author="Kjetil Jacobsen, Markus F.X.J. Oberhumer",
    author_email="kjetilja@cs.uit.no, markus@oberhumer.com",
    maintainer="Kjetil Jacobsen, Markus F.X.J. Oberhumer",
    maintainer_email="kjetilja@cs.uit.no, markus@oberhumer.com",
    url="http://pycurl.sourceforge.net/",
    license="GNU Lesser General Public License (LGPL)",
    data_files = [
        # list of tuples with (path to install to, a list of files)
        (os.path.join("doc", "pycurl"), [
            "COPYING", "INSTALL", "README", "TODO",
        ]),
        (os.path.join("doc", "pycurl", "examples"), [
            os.path.join("examples", "basicfirst.py"),
            os.path.join("examples", "curl.py"),
            os.path.join("examples", "gtkhtml_demo.py"),
            os.path.join("examples", "retriever.py"),
            os.path.join("examples", "sfquery.py"),
            os.path.join("examples", "xmlrpc_curl.py"),
        ]),
    ],
    ext_modules=[ext],
    long_description="""
This module provides Python bindings for the cURL library.""",
)

##print distutils.__version__
setup_args["licence"] = setup_args["license"]
if LooseVersion(distutils.__version__) > LooseVersion("1.0.1"):
    setup_args["platforms"] = "All"

apply(setup, (), setup_args)

