#! /usr/bin/env python

# $Id$

"""Setup script for the PycURL module distribution."""

import os, sys
from distutils.core import setup
from distutils.extension import Extension
from string import strip, split

if sys.platform == "win32":
    # Windows users have to configure the next thress path params
    # to match their libcurl installation
    include_dirs = [r'C:\User\clib\libcurl\include']
    library_dirs = [r'C:\User\clib\libcurl\lib']
    extra_objects = [r'C:\User\clib\libcurl\lib\libcurl.lib']
    # These should be fine as they are, please notify if they need updates
    libraries = ['libcurl', 'zlib', 'msvcrt', 'libcmt', 'wsock32', 'advapi32']
    runtime_library_dirs = []
    extra_link_args = ['/NODEFAULTLIB:LIBCMTD.lib']
else:
    # Otherwise, be brave and try to figure out dynamically through 
    # curl-config
    include_dirs = []
    cflags=split(strip(os.popen('curl-config --cflags').read()), ' ')
    for e in cflags:
        if e[:2] == '-I':
            include_dirs.append(e[2:])
    library_dirs = []
    libs = split(strip(os.popen('curl-config --libs').read()), ' ')
    for e in libs:
        if e[:2] == '-L':
            library_dirs.append(e[2:])
            libs.remove(e)
    libraries = ["curl"]
    extra_link_args = libs 
    runtime_library_dirs = []
    extra_objects = []

long_description = "PycURL -- cURL library module for Python"

###############################################################################

setup (	name="pycurl",
      	version="0.4.3",
      	description="PycURL -- cURL library module for Python",
      	author="Kjetil Jacobsen",
      	author_email="kjetilja@cs.uit.no",
      	url="http://pycurl.sourceforge.net/",
      	ext_modules=[Extension(name="pycurl", 
                               sources=["src/curl.c"],
                               include_dirs=include_dirs,
                               library_dirs=library_dirs,
                               runtime_library_dirs=runtime_library_dirs,
                               libraries=libraries,
                               extra_link_args=extra_link_args,
                               extra_objects=extra_objects)]
        )	
