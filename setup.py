#! /usr/bin/env python
# vi:ts=4:et

# $Id$

"""Setup script for the PycURL module distribution."""

VERSION = "7.10.2"

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


def scan_argv(s, default):
    p = default
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if string.find(arg, s) == 0:
            p = arg[len(s):]
            assert p, arg
            del sys.argv[i]
        else:
            i = i + 1
    ##print sys.argv
    return p


if sys.platform == "win32":
    # Windows users have to configure the CURL_DIR path parameter to match
    # their cURL source installation.  The path set here is just an example
    # and thus unlikely to match your installation.
    CURL_DIR = r"c:\src\curl-7.10.1"
    CURL_DIR = scan_argv("--curl-dir=", CURL_DIR)
    print "Using curl directory:", CURL_DIR
    assert os.path.isdir(CURL_DIR), "please check CURL_DIR in setup.py"
    include_dirs.append(os.path.join(CURL_DIR, "include"))
    extra_objects.append(os.path.join(CURL_DIR, "lib", "libcurl.lib"))
else:
    # Find out the rest the hard way
    CURL_CONFIG = "curl-config"
    CURL_CONFIG = scan_argv("--curl-config=", CURL_CONFIG)
    d = os.popen("%s --version" % CURL_CONFIG).read()
    if d:
        d = string.strip(d)
    if not d:
        raise Exception, ("`%s' not found -- please install the libcurl development files" % CURL_CONFIG)
    print "Using %s (%s)" % (CURL_CONFIG, d)
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
            "ChangeLog", "COPYING", "INSTALL", "README", "TODO",
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

if __name__ == "__main__":
    for o in ext.extra_objects:
        assert os.path.isfile(o), o
    apply(setup, (), setup_args)

