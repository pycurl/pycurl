#!/usr/bin/env python

# $Id$

from distutils.core import setup, Extension

setup(name="pycurl",
      version="0.4.2",
      description="PycURL -- cURL library module for Python",
      author="Kjetil Jacobsen",
      author_email="kjetilja@cs.uit.no",
      url="http://pycurl.sourceforge.net/",
      ext_modules=[Extension("pycurl", ["src/curl.c"],
                             include_dirs=["include"],
                             libraries=["curl"]),]
      )
