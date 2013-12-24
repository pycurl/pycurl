#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
# vi:ts=4:et
# $Id$

"""Setup script for the PycURL module distribution."""

PACKAGE = "pycurl"
PY_PACKAGE = "curl"
VERSION = "7.19.0.3"

import glob, os, re, sys, string, subprocess
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
        if str.find(arg, s) == 0:
            p = arg[len(s):]
            assert p, arg
            del sys.argv[i]
        else:
            i = i + 1
    ##print sys.argv
    return p


# append contents of an environment variable to library_dirs[]
def add_libdirs(envvar, sep, fatal=0):
    v = os.environ.get(envvar)
    if not v:
        return
    for dir in str.split(v, sep):
        dir = str.strip(dir)
        if not dir:
            continue
        dir = os.path.normpath(dir)
        if os.path.isdir(dir):
            if not dir in library_dirs:
                library_dirs.append(dir)
        elif fatal:
            print("FATAL: bad directory %s in environment variable %s" % (dir, envvar))
            sys.exit(1)


if sys.platform == "win32":
    # Windows users have to configure the curl_dir path parameter to match
    # their cURL source installation.  The path set here is just an example
    # and thus unlikely to match your installation.
    curl_dir = scan_argv("--curl-dir=", None)
    if curl_dir is None:
        fail("Please specify --curl-dir=/path/to/built/libcurl")
    if not os.path.exists(curl_dir):
        fail("Curl directory does not exist: %s" % curl_dir)
    if not os.path.isdir(curl_dir):
        fail("Curl directory is not a directory: %s" % curl_dir)
    print("Using curl directory: %s" % curl_dir)
    include_dirs.append(os.path.join(curl_dir, "include"))
    libcurl_lib_path = os.path.join(curl_dir, "lib", "libcurl.lib")
    if not os.path.exists(libcurl_lib_path):
        fail("libcurl.lib does not exist at %s.\nCurl directory must point to compiled libcurl (bin/include/lib subdirectories): %s" %(libcurl_lib_path, curl_dir))
    extra_objects.append(libcurl_lib_path)
    extra_link_args.extend(["gdi32.lib", "wldap32.lib", "winmm.lib", "ws2_32.lib",])
    add_libdirs("LIB", ";")
    if str.find(sys.version, "MSC") >= 0:
        extra_compile_args.append("-O2")
        extra_compile_args.append("-GF")        # enable read-only string pooling
        extra_compile_args.append("-WX")        # treat warnings as errors
        p = subprocess.Popen(['cl.exe'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        match = re.search(r'Version (\d+)', err.split("\n")[0])
        if match and int(match.group(1)) < 16:
            # option removed in vs 2010:
            # connect.microsoft.com/VisualStudio/feedback/details/475896/link-fatal-error-lnk1117-syntax-error-in-option-opt-nowin98/
            extra_link_args.append("/opt:nowin98")  # use small section alignment

        # workaround for distutils/msi version requirement per
        # epydoc.sourceforge.net/stdlib/distutils.version.StrictVersion-class.html -
        # only x.y.z version numbers are supported, whereas our versions might be x.y.z.p.
        # bugs.python.org/issue6040#msg133094
        from distutils.command.bdist_msi import bdist_msi
        import inspect
        import types
        import re
        
        class bdist_msi_version_hack(bdist_msi):
            """ MSI builder requires version to be in the x.x.x format """
            def run(self):
                def monkey_get_version(self):
                    """ monkey patch replacement for metadata.get_version() that
                            returns MSI compatible version string for bdist_msi
                    """
                    # get filename of the calling function
                    if inspect.stack()[1][1].endswith('bdist_msi.py'):
                        # strip revision from version (if any), e.g. 11.0.0-r31546
                        match = re.match(r'(\d+\.\d+\.\d+)', self.version)
                        assert match
                        return match.group(1)
                    else:
                        return self.version

                # monkeypatching get_version() call for DistributionMetadata
                self.distribution.metadata.get_version = \
                    types.MethodType(monkey_get_version, self.distribution.metadata)
                bdist_msi.run(self)
else:
    # Find out the rest the hard way
    OPENSSL_DIR = scan_argv("--openssl-dir=", "")
    if OPENSSL_DIR != "":
        include_dirs.append(os.path.join(OPENSSL_DIR, "include"))
    CURL_CONFIG = os.environ.get('PYCURL_CURL_CONFIG', "curl-config")
    CURL_CONFIG = scan_argv("--curl-config=", CURL_CONFIG)
    d = os.popen("'%s' --version" % CURL_CONFIG).read()
    if d:
        d = str.strip(d)
    if not d:
        raise Exception("`%s' not found -- please install the libcurl development files or specify --curl-config=/path/to/curl-config" % CURL_CONFIG)
    print("Using %s (%s)" % (CURL_CONFIG, d))
    for e in split_quoted(os.popen("'%s' --cflags" % CURL_CONFIG).read()):
        if e[:2] == "-I":
            # do not add /usr/include
            if not re.search(r"^\/+usr\/+include\/*$", e[2:]):
                include_dirs.append(e[2:])
        else:
            extra_compile_args.append(e)

    # Run curl-config --libs and --static-libs.  Some platforms may not
    # support one or the other of these curl-config options, so gracefully
    # tolerate failure of either, but not both.
    optbuf = ""
    for option in ["--libs", "--static-libs"]:
        p = subprocess.Popen("'%s' %s" % (CURL_CONFIG, option), shell=True,
            stdout=subprocess.PIPE)
        (stdout, stderr) = p.communicate()
        if p.wait() == 0:
            optbuf += stdout.decode()
    if optbuf == "":
        raise Exception("Neither curl-config --libs nor curl-config --static-libs" +
            " produced output")
    libs = split_quoted(optbuf)

    for e in libs:
        if e[:2] == "-l":
            libraries.append(e[2:])
            if e[2:] == 'ssl':
                define_macros.append(('HAVE_CURL_OPENSSL', 1))
            if e[2:] == 'gnutls':
                define_macros.append(('HAVE_CURL_GNUTLS', 1))
            if e[2:] == 'ssl3':
                define_macros.append(('HAVE_CURL_NSS', 1))
        elif e[:2] == "-L":
            library_dirs.append(e[2:])
        else:
            extra_link_args.append(e)
    for e in split_quoted(os.popen("'%s' --features" % CURL_CONFIG).read()):
        if e == 'SSL':
            define_macros.append(('HAVE_CURL_SSL', 1))
    if not libraries:
        libraries.append("curl")
    # Add extra compile flag for MacOS X
    if sys.platform[:-1] == "darwin":
        extra_link_args.append("-flat_namespace")


###############################################################################

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
    files = ["ChangeLog", "COPYING", "COPYING2", "INSTALL", "README.rst", "TODO",]
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

setup_args = dict(
    name=PACKAGE,
    version=VERSION,
    description="PycURL -- cURL library module for Python",
    author="Kjetil Jacobsen, Markus F.X.J. Oberhumer",
    author_email="kjetilja at gmail.com, markus at oberhumer.com",
    maintainer="Oleg Pudeyev",
    maintainer_email="oleg@bsdpower.com",
    url="http://pycurl.sourceforge.net/",
    download_url="http://pycurl.sourceforge.net/download/",
    license="LGPL/MIT",
    keywords=['curl', 'libcurl', 'urllib', 'wget', 'download', 'file transfer',
        'http', 'www'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Internet :: File Transfer Protocol (FTP)',
        'Topic :: Internet :: WWW/HTTP',
    ],
    data_files=get_data_files(),
    ext_modules=[ext],
    packages=[PY_PACKAGE],
    package_dir={ PY_PACKAGE: os.path.join('python', 'curl') },
    long_description="""
This module provides Python bindings for the cURL library.""",
)

if sys.platform == "win32":
        setup_args['cmdclass'] = {'bdist_msi': bdist_msi_version_hack}

##print distutils.__version__
if LooseVersion(distutils.__version__) > LooseVersion("1.0.1"):
    setup_args["platforms"] = "All"
if LooseVersion(distutils.__version__) < LooseVersion("1.0.3"):
    setup_args["licence"] = setup_args["license"]

if __name__ == "__main__":
    for o in ext.extra_objects:
        assert os.path.isfile(o), o
    setup(**setup_args)
