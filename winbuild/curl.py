import os.path, shutil, os
from .utils import *
from .builder import *
from .zlib import *
from .openssl import *
from .cares import *
from .ssh import *
from .nghttp_gmake import *

class LibcurlBuilder(StandardBuilder):
    def build(self):
        curl_dir = self.standard_fetch_extract(
            'https://curl.haxx.se/download/curl-%(my_version)s.tar.gz')
    
        with in_dir(os.path.join(curl_dir, 'winbuild')):
            if self.bconf.vc_version == 'vc9':
                # normaliz.lib in vc9 does not have the symbols libcurl
                # needs for winidn.
                # Handily we have a working normaliz.lib in vc14.
                # Let's take the working one and copy it locally.
                os.mkdir('support')
                if self.bconf.bitness == 32:
                    shutil.copy(os.path.join(self.bconf.windows_sdk_path, 'lib', 'normaliz.lib'),
                        os.path.join('support', 'normaliz.lib'))
                else:
                    shutil.copy(os.path.join(self.bconf.windows_sdk_path, 'lib', 'x64', 'normaliz.lib'),
                        os.path.join('support', 'normaliz.lib'))
            
            with self.execute_batch() as b:
                b.add("patch -p1 < %s" %
                    require_file_exists(os.path.join(self.bconf.winbuild_patch_root, 'libcurl-fix-zlib-references.patch')))
                if self.use_dlls:
                    dll_or_static = 'dll'
                else:
                    dll_or_static = 'static'
                extra_options = ' mode=%s' % dll_or_static
                if self.bconf.vc_version == 'vc9':
                    # use normaliz.lib from msvc14/more recent windows sdk
                    b.add("set lib=%s;%%lib%%" % os.path.abspath('support'))
                if self.bconf.use_zlib:
                    zlib_builder = ZlibBuilder(bconf=self.bconf)
                    b.add("set include=%%include%%;%s" % zlib_builder.include_path)
                    b.add("set lib=%%lib%%;%s" % zlib_builder.lib_path)
                    extra_options += ' WITH_ZLIB=%s' % dll_or_static
                if self.bconf.use_openssl:
                    openssl_builder = OpensslBuilder(bconf=self.bconf)
                    b.add("set include=%%include%%;%s" % openssl_builder.include_path)
                    b.add("set lib=%%lib%%;%s" % openssl_builder.lib_path)
                    extra_options += ' WITH_SSL=%s' % dll_or_static
                if self.bconf.use_cares:
                    cares_builder = CaresBuilder(bconf=self.bconf)
                    b.add("set include=%%include%%;%s" % cares_builder.include_path)
                    b.add("set lib=%%lib%%;%s" % cares_builder.lib_path)
                    extra_options += ' WITH_CARES=%s' % dll_or_static
                if self.bconf.use_libssh2:
                    libssh2_builder = Libssh2Builder(bconf=self.bconf)
                    b.add("set include=%%include%%;%s" % libssh2_builder.include_path)
                    b.add("set lib=%%lib%%;%s" % libssh2_builder.lib_path)
                    extra_options += ' WITH_SSH2=%s' % dll_or_static
                if self.bconf.use_nghttp2:
                    nghttp2_builder = Nghttp2Builder(bconf=self.bconf)
                    b.add("set include=%%include%%;%s" % nghttp2_builder.include_path)
                    b.add("set lib=%%lib%%;%s" % nghttp2_builder.lib_path)
                    extra_options += ' WITH_NGHTTP2=%s NGHTTP2_STATICLIB=1' % dll_or_static
                if self.bconf.use_libidn:
                    libidn_builder = LibidnBuilder(bconf=self.bconf)
                    b.add("set include=%%include%%;%s" % libidn_builder.include_path)
                    b.add("set lib=%%lib%%;%s" % libidn_builder.lib_path)
                    extra_options += ' WITH_LIBIDN=%s' % dll_or_static
                if self.bconf.openssl_version_tuple >= (1, 1):
                    # openssl 1.1.0
                    # https://curl.haxx.se/mail/lib-2016-08/0104.html
                    # https://github.com/curl/curl/issues/984
                    # crypt32.lib: http://stackoverflow.com/questions/37522654/linking-with-openssl-lib-statically
                    extra_options += ' MAKE="NMAKE /e" SSL_LIBS="libssl.lib libcrypto.lib crypt32.lib"'
                # https://github.com/curl/curl/issues/1863
                extra_options += ' VC=%s' % self.bconf.vc_version[2:]
                
                # curl uses winidn APIs that do not exist in msvc9:
                # https://github.com/curl/curl/issues/1863
                # We work around the msvc9 deficiency by using
                # msvc14 normaliz.lib on vc9.
                extra_options += ' ENABLE_IDN=yes'
                
                b.add("nmake /f Makefile.vc %s" % extra_options)
        
        # assemble dist - figure out where libcurl put its files
        # and move them to a more reasonable location
        with in_dir(curl_dir):
            subdirs = sorted(os.listdir('builds'))
            if len(subdirs) != 3:
                raise Exception('Should be 3 directories here')
            expected_dir = subdirs.pop(0)
            for dir in subdirs:
                if not dir.startswith(expected_dir):
                    raise Exception('%s does not start with %s' % (dir, expected_dir))
                    
            os.rename(os.path.join('builds', expected_dir), 'dist')
            if self.bconf.vc_version == 'vc9':
                # need this normaliz.lib to build pycurl later on
                shutil.copy('winbuild/support/normaliz.lib', 'dist/lib/normaliz.lib')
                
            # need libcurl.lib to build pycurl with --curl-dir argument
            shutil.copy('dist/lib/libcurl_a.lib', 'dist/lib/libcurl.lib')

    @property
    def dll_paths(self):
        return [
            os.path.join(self.bin_path, 'libcurl.dll'),
        ]
