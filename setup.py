#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id$

"""Setup script for the PycURL module distribution."""

PACKAGE = "pycurl"
PY_PACKAGE = "curl"
VERSION = "7.10.5"

import glob, os, re, sys, string
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


# append contents of an environment variable to library_dirs[]
def add_libdirs(envvar, sep, fatal=1):
    v = os.environ.get(envvar)
    if not v:
        return
    for dir in string.split(v, sep):
        dir = string.strip(dir)
        if not dir:
            continue
        dir = os.path.normpath(dir)
        if os.path.isdir(dir):
            if not dir in library_dirs:
                library_dirs.append(dir)
        elif fatal:
            print "FATAL: bad directory %s in environment variable %s" % (dir, envvar)
            sys.exit(1)


if sys.platform == "win32":
    # Windows users have to configure the CURL_DIR path parameter to match
    # their cURL source installation.  The path set here is just an example
    # and thus unlikely to match your installation.
    CURL_DIR = r"c:\src\build\curl-7.10.5"
    CURL_DIR = scan_argv("--curl-dir=", CURL_DIR)
    print "Using curl directory:", CURL_DIR
    assert os.path.isdir(CURL_DIR), "please check CURL_DIR in setup.py"
    include_dirs.append(os.path.join(CURL_DIR, "include"))
    extra_objects.append(os.path.join(CURL_DIR, "lib", "libcurl.lib"))
    extra_link_args.extend(["gdi32.lib", "winmm.lib", "ws2_32.lib",])
    add_libdirs("LIB", ";")
    if string.find(sys.version, "MSC") != 1:
        ##extra_compile_args.append("-GF")
        extra_compile_args.append("-Gy")
        extra_compile_args.append("-WX")
else:
    # Find out the rest the hard way
    CURL_CONFIG = "curl-config"
    CURL_CONFIG = scan_argv("--curl-config=", CURL_CONFIG)
    d = os.popen("'%s' --version" % CURL_CONFIG).read()
    if d:
        d = string.strip(d)
    if not d:
        raise Exception, ("`%s' not found -- please install the libcurl development files" % CURL_CONFIG)
    print "Using %s (%s)" % (CURL_CONFIG, d)
    for e in split_quoted(os.popen("'%s' --cflags" % CURL_CONFIG).read()):
        if e[:2] == "-I":
            # do not add /usr/include
            if not re.search(r"^\/+usr\/+include\/*$", e[2:]):
                include_dirs.append(e[2:])
        else:
            extra_compile_args.append(e)
    for e in split_quoted(os.popen("'%s' --libs" % CURL_CONFIG).read()):
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
    name=PACKAGE,
    sources=[
        os.path.join("src", "pycurl.c"),
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


###############################################################################

# prepare data_files

def get_data_files():
    # a list of tuples with (path to install to, a list of local files)
    data_files = []
    if sys.platform == "win32":
        datadir = os.path.join("doc", PACKAGE)
    else:
        datadir = os.path.join("share", "doc", PACKAGE)
    #
    files = ["ChangeLog", "COPYING", "INSTALL", "README", "TODO",]
    if files:
        data_files.append((os.path.join(datadir), files))
    files = glob.glob(os.path.join("doc", "*.html"))
    if files:
        data_files.append((os.path.join(datadir, "html"), files))
    files = glob.glob(os.path.join("examples", "*.py"))
    if files:
        data_files.append((os.path.join(datadir, "examples"), files))
    files = glob.glob(os.path.join("tests", "*.py"))
    if files:
        data_files.append((os.path.join(datadir, "tests"), files))
    #
    assert data_files
    for install_dir, files in data_files:
        assert files
        for f in files:
            assert os.path.isfile(f), (f, install_dir)
    return data_files

##print get_data_files(); sys.exit(1)


###############################################################################

setup_args = get_kw(
    name=PACKAGE,
    version=VERSION,
    description="PycURL -- cURL library module for Python",
    author="Kjetil Jacobsen, Markus F.X.J. Oberhumer",
    author_email="kjetilja@cs.uit.no, markus@oberhumer.com",
    maintainer="Kjetil Jacobsen, Markus F.X.J. Oberhumer",
    maintainer_email="kjetilja@cs.uit.no, markus@oberhumer.com",
    url="http://pycurl.sourceforge.net/",
    license="GNU Lesser General Public License (LGPL)",
    data_files=get_data_files(),
    ext_modules=[ext],
    long_description="""
This module provides Python bindings for the cURL library.""",
)

# FIXME - which Python version do we want to support ???
if sys.version >= "2.2":
    setup_args["packages"] = [PY_PACKAGE]
    setup_args["package_dir"] = { PY_PACKAGE: os.path.join('python', 'curl') }


##print distutils.__version__
if LooseVersion(distutils.__version__) > LooseVersion("1.0.1"):
    setup_args["platforms"] = "All"
if LooseVersion(distutils.__version__) < LooseVersion("1.0.3"):
    setup_args["licence"] = setup_args["license"]

if __name__ == "__main__":
    for o in ext.extra_objects:
        assert os.path.isfile(o), o
    apply(setup, (), setup_args)

