#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

"""Setup script for the PycURL module distribution."""

PACKAGE = "pycurl"
PY_PACKAGE = "curl"
VERSION = "7.44.0"

import glob, os, re, sys, subprocess
import distutils
try:
    import wheel
    if wheel:
        from setuptools import setup
except ImportError:
    from distutils.core import setup
from distutils.extension import Extension
from distutils.util import split_quoted
from distutils.version import LooseVersion

py3 = sys.version_info[0] == 3

try:
    # python 2
    exception_base = StandardError
except NameError:
    # python 3
    exception_base = Exception
class ConfigurationError(exception_base):
    pass


def fail(msg):
    sys.stderr.write(msg + "\n")
    exit(10)


def scan_argv(argv, s, default=None):
    p = default
    i = 1
    while i < len(argv):
        arg = argv[i]
        if s.endswith('='):
            if str.find(arg, s) == 0:
                # --option=value
                p = arg[len(s):]
                if s != '--openssl-lib-name=':
                    assert p, arg
                del argv[i]
            else:
                i += 1
        else:
            if s == arg:
                # --option
                # set value to True
                p = True
                del argv[i]
            else:
                i = i + 1
    ##print argv
    return p


def scan_argvs(argv, s):
    if not s.endswith('='):
        raise Exception('specification must end with =')
    p = []
    i = 1
    while i < len(argv):
        arg = argv[i]
        if str.find(arg, s) == 0:
            # --option=value
            p.append(arg[len(s):])
            if s != '--openssl-lib-name=':
                assert p[-1], arg
            del argv[i]
        else:
            i = i + 1
    ##print argv
    return p


class ExtensionConfiguration(object):
    def __init__(self, argv=[]):
        # we mutate argv, this is necessary because
        # setuptools does not recognize pycurl-specific options
        self.argv = argv
        self.original_argv = argv[:]
        self.include_dirs = []
        self.define_macros = [("PYCURL_VERSION", '"%s"' % VERSION)]
        self.library_dirs = []
        self.libraries = []
        self.runtime_library_dirs = []
        self.extra_objects = []
        self.extra_compile_args = []
        self.extra_link_args = []
        self.ssl_lib_detected = None

        self.configure()

    @property
    def define_symbols(self):
        return [symbol for symbol, expansion in self.define_macros]

    # append contents of an environment variable to library_dirs[]
    def add_libdirs(self, envvar, sep, fatal=False):
        v = os.environ.get(envvar)
        if not v:
            return
        for dir in str.split(v, sep):
            dir = str.strip(dir)
            if not dir:
                continue
            dir = os.path.normpath(dir)
            if os.path.isdir(dir):
                if not dir in self.library_dirs:
                    self.library_dirs.append(dir)
            elif fatal:
                fail("FATAL: bad directory %s in environment variable %s" % (dir, envvar))

    def detect_features(self):
        p = subprocess.Popen((self.curl_config(), '--features'),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if p.wait() != 0:
            msg = "Problem running `%s' --features" % self.curl_config()
            if stderr:
                msg += ":\n" + stderr.decode()
            raise ConfigurationError(msg)
        curl_has_ssl = False
        for feature in split_quoted(stdout.decode()):
            if feature == 'SSL':
                # this means any ssl library, not just openssl.
                # we set the ssl flag to check for ssl library mismatch
                # at link time and run time
                self.define_macros.append(('HAVE_CURL_SSL', 1))
                curl_has_ssl = True
        self.curl_has_ssl = curl_has_ssl

    def ssl_options(self):
        return {
            '--with-openssl': self.using_openssl,
            '--with-ssl': self.using_openssl,
            '--with-wolfssl': self.using_wolfssl,
            '--with-gnutls': self.using_gnutls,
            '--with-nss': self.using_nss,
            '--with-mbedtls': self.using_mbedtls,
        }

    def detect_ssl_option(self):
        for option in self.ssl_options():
            if scan_argv(self.argv, option) is not None:
                for other_option in self.ssl_options():
                    if option != other_option:
                        if scan_argv(self.argv, other_option) is not None:
                            raise ConfigurationError('Cannot give both %s and %s' % (option, other_option))

                return option

    def detect_ssl_backend(self):
        ssl_lib_detected = None

        if 'PYCURL_SSL_LIBRARY' in os.environ:
            ssl_lib = os.environ['PYCURL_SSL_LIBRARY']
            if ssl_lib in ['openssl', 'wolfssl', 'gnutls', 'nss', 'mbedtls']:
                ssl_lib_detected = ssl_lib
                getattr(self, 'using_%s' % ssl_lib)()
            else:
                raise ConfigurationError('Invalid value "%s" for PYCURL_SSL_LIBRARY' % ssl_lib)

        option = self.detect_ssl_option()
        if option:
            ssl_lib_detected = option.replace('--with-', '')
            self.ssl_options()[option]()

        # ssl detection - ssl libraries are added
        if not ssl_lib_detected:
            libcurl_dll_path = scan_argv(self.argv, "--libcurl-dll=")
            if libcurl_dll_path is not None:
                ssl_lib_detected = self.detect_ssl_lib_from_libcurl_dll(libcurl_dll_path)

        if not ssl_lib_detected:
            ssl_lib_detected = self.detect_ssl_lib_using_curl_config()

        if not ssl_lib_detected:
            # self.sslhintbuf is a hack
            for arg in split_quoted(self.sslhintbuf):
                if arg[:2] == "-l":
                    if arg[2:] == 'ssl':
                        self.using_openssl()
                        ssl_lib_detected = 'openssl'
                        break
                    if arg[2:] == 'wolfssl':
                        self.using_wolfssl()
                        ssl_lib_detected = 'wolfssl'
                        break
                    if arg[2:] == 'gnutls':
                        self.using_gnutls()
                        ssl_lib_detected = 'gnutls'
                        break
                    if arg[2:] == 'ssl3':
                        self.using_nss()
                        ssl_lib_detected = 'nss'
                        break
                    if arg[2:] == 'mbedtls':
                        self.using_mbedtls()
                        ssl_lib_detected = 'mbedtls'
                        break

        if not ssl_lib_detected and len(self.argv) == len(self.original_argv) \
                and not os.environ.get('PYCURL_CURL_CONFIG') \
                and not os.environ.get('PYCURL_SSL_LIBRARY'):
            # this path should only be taken when no options or
            # configuration environment variables are given to setup.py
            ssl_lib_detected = self.detect_ssl_lib_on_centos6_plus()

        self.ssl_lib_detected = ssl_lib_detected

    def curl_config(self):
        try:
            return self._curl_config
        except AttributeError:
            curl_config = os.environ.get('PYCURL_CURL_CONFIG', "curl-config")
            curl_config = scan_argv(self.argv, "--curl-config=", curl_config)
            self._curl_config = curl_config
            return curl_config

    def configure_unix(self):
        OPENSSL_DIR = scan_argv(self.argv, "--openssl-dir=")
        if OPENSSL_DIR is not None:
            self.include_dirs.append(os.path.join(OPENSSL_DIR, "include"))
            self.library_dirs.append(os.path.join(OPENSSL_DIR, "lib"))
        try:
            p = subprocess.Popen((self.curl_config(), '--version'),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            exc = sys.exc_info()[1]
            msg = 'Could not run curl-config: %s' % str(exc)
            raise ConfigurationError(msg)
        stdout, stderr = p.communicate()
        if p.wait() != 0:
            msg = "`%s' not found -- please install the libcurl development files or specify --curl-config=/path/to/curl-config" % self.curl_config()
            if stderr:
                msg += ":\n" + stderr.decode()
            raise ConfigurationError(msg)
        libcurl_version = stdout.decode().strip()
        print("Using %s (%s)" % (self.curl_config(), libcurl_version))
        p = subprocess.Popen((self.curl_config(), '--cflags'),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if p.wait() != 0:
            msg = "Problem running `%s' --cflags" % self.curl_config()
            if stderr:
                msg += ":\n" + stderr.decode()
            raise ConfigurationError(msg)
        for arg in split_quoted(stdout.decode()):
            if arg[:2] == "-I":
                # do not add /usr/include
                if not re.search(r"^\/+usr\/+include\/*$", arg[2:]):
                    self.include_dirs.append(arg[2:])
            else:
                self.extra_compile_args.append(arg)

        # Obtain linker flags/libraries to link against.
        # In theory, all we should need is `curl-config --libs`.
        # Apparently on some platforms --libs fails and --static-libs works,
        # so try that.
        # If --libs succeeds do not try --static-libs; see
        # https://github.com/pycurl/pycurl/issues/52 for more details.
        # If neither --libs nor --static-libs work, fail.
        #
        # --libs/--static-libs are also used for SSL detection.
        # libcurl may be configured such that --libs only includes -lcurl
        # without any of libcurl's dependent libraries, but the dependent
        # libraries would be included in --static-libs (unless libcurl
        # was built with static libraries disabled).
        # Therefore we largely ignore (see below) --static-libs output for
        # libraries and flags if --libs succeeded, but consult both outputs
        # for hints as to which SSL library libcurl is linked against.
        # More information: https://github.com/pycurl/pycurl/pull/147
        #
        # The final point is we should link agaist the SSL library in use
        # even if libcurl does not tell us to, because *we* invoke functions
        # in that SSL library. This means any SSL libraries found in
        # --static-libs are forwarded to our libraries.
        optbuf = ''
        sslhintbuf = ''
        errtext = ''
        for option in ["--libs", "--static-libs"]:
            p = subprocess.Popen((self.curl_config(), option),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            if p.wait() == 0:
                if optbuf == '':
                    # first successful call
                    optbuf = stdout.decode()
                    # optbuf only has output from this call
                    sslhintbuf += optbuf
                else:
                    # second successful call
                    sslhintbuf += stdout.decode()
            else:
                if optbuf == '':
                    # no successful call yet
                    errtext += stderr.decode()
                else:
                    # first call succeeded and second call failed
                    # ignore stderr and the error exit
                    pass
        if optbuf == "":
            msg = "Neither curl-config --libs nor curl-config --static-libs" +\
                " succeeded and produced output"
            if errtext:
                msg += ":\n" + errtext
            raise ConfigurationError(msg)

        # hack
        self.sslhintbuf = sslhintbuf

        self.detect_features()
        self.ssl_lib_detected = None
        if self.curl_has_ssl:
            self.detect_ssl_backend()

            if not self.ssl_lib_detected:
                sys.stderr.write('''\
Warning: libcurl is configured to use SSL, but we have not been able to \
determine which SSL backend it is using. If your Curl is built against \
OpenSSL, LibreSSL, BoringSSL, GnuTLS, NSS or mbedTLS please specify the SSL backend \
manually. For other SSL backends please ignore this message.''')
        else:
            if self.detect_ssl_option():
                sys.stderr.write("Warning: SSL backend specified manually but libcurl does not use SSL\n")

        # libraries and options - all libraries and options are forwarded
        # but if --libs succeeded, --static-libs output is ignored
        for arg in split_quoted(optbuf):
            if arg[:2] == "-l":
                self.libraries.append(arg[2:])
            elif arg[:2] == "-L":
                self.library_dirs.append(arg[2:])
            else:
                self.extra_link_args.append(arg)

        if not self.libraries:
            self.libraries.append("curl")

        # Add extra compile flag for MacOS X
        if sys.platform.startswith('darwin'):
            self.extra_link_args.append("-flat_namespace")

        # Recognize --avoid-stdio on Unix so that it can be tested
        self.check_avoid_stdio()

    def detect_ssl_lib_from_libcurl_dll(self, libcurl_dll_path):
        ssl_lib_detected = None
        curl_version_info = self.get_curl_version_info(libcurl_dll_path)
        ssl_version = curl_version_info.ssl_version
        if py3:
            # ssl_version is bytes on python 3
            ssl_version = ssl_version.decode('ascii')
        if ssl_version.startswith('OpenSSL/') or ssl_version.startswith('LibreSSL/'):
            self.using_openssl()
            ssl_lib_detected = 'openssl'
        elif ssl_version.startswith('GnuTLS/'):
            self.using_gnutls()
            ssl_lib_detected = 'gnutls'
        elif ssl_version.startswith('NSS/'):
            self.using_nss()
            ssl_lib_detected = 'nss'
        elif ssl_version.startswith('mbedTLS/'):
            self.using_mbedtls()
            ssl_lib_detected = 'mbedtls'
        return ssl_lib_detected

    def detect_ssl_lib_on_centos6_plus(self):
        import platform
        from ctypes.util import find_library
        os_name = platform.system()
        if os_name != 'Linux' or not hasattr(platform, 'dist'):
            return False
        dist_name, dist_version, _ = platform.dist()
        dist_version = dist_version.split('.')[0]
        if dist_name != 'centos' or int(dist_version) < 6:
            return False
        libcurl_dll_path = find_library('curl')
        print('libcurl_dll_path = "%s"' % libcurl_dll_path)
        return self.detect_ssl_lib_from_libcurl_dll(libcurl_dll_path)

    def detect_ssl_lib_using_curl_config(self):
        ssl_lib_detected = None
        p = subprocess.Popen((self.curl_config(), '--ssl-backends'),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if p.wait() != 0:
            # curl-config --ssl-backends is not supported on older curl versions
            return None
        ssl_version = stdout.decode()
        if ssl_version.startswith('OpenSSL') or ssl_version.startswith('LibreSSL'):
            self.using_openssl()
            ssl_lib_detected = 'openssl'
        elif ssl_version.startswith('GnuTLS'):
            self.using_gnutls()
            ssl_lib_detected = 'gnutls'
        elif ssl_version.startswith('NSS'):
            self.using_nss()
            ssl_lib_detected = 'nss'
        elif ssl_version.startswith('mbedTLS'):
            self.using_mbedtls()
            ssl_lib_detected = 'mbedtls'
        return ssl_lib_detected

    def configure_windows(self):
        # Windows users have to pass --curl-dir parameter to specify path
        # to libcurl, because there is no curl-config on windows at all.
        curl_dir = scan_argv(self.argv, "--curl-dir=")
        if curl_dir is None:
            fail("Please specify --curl-dir=/path/to/built/libcurl")
        if not os.path.exists(curl_dir):
            fail("Curl directory does not exist: %s" % curl_dir)
        if not os.path.isdir(curl_dir):
            fail("Curl directory is not a directory: %s" % curl_dir)
        print("Using curl directory: %s" % curl_dir)
        self.include_dirs.append(os.path.join(curl_dir, "include"))

        # libcurl windows documentation states that for linking against libcurl
        # dll, the import library name is libcurl_imp.lib.
        # For libcurl 7.46.0, the library name is libcurl.lib.
        # And static library name is libcurl_a.lib by default as of libcurl 7.46.0.
        # override with: --libcurl-lib-name=libcurl_imp.lib
        curl_lib_name = scan_argv(self.argv, '--libcurl-lib-name=', 'libcurl.lib')

        # openssl 1.1.0 changed its library names
        # from libeay32.lib/ssleay32.lib to libcrypto.lib/libssl.lib.
        # at the same time they dropped thread locking callback interface,
        # meaning the correct usage of this option is --openssl-lib-name=""
        self.openssl_lib_name = scan_argv(self.argv, '--openssl-lib-name=', 'libeay32.lib')

        for lib in scan_argvs(self.argv, '--link-arg='):
            self.extra_link_args.append(lib)

        if scan_argv(self.argv, "--use-libcurl-dll") is not None:
            libcurl_lib_path = os.path.join(curl_dir, "lib", curl_lib_name)
            self.extra_link_args.extend(["ws2_32.lib"])
            if str.find(sys.version, "MSC") >= 0:
                # build a dll
                self.extra_compile_args.append("-MD")
        else:
            self.extra_compile_args.append("-DCURL_STATICLIB")
            libcurl_lib_path = os.path.join(curl_dir, "lib", curl_lib_name)
            self.extra_link_args.extend(["gdi32.lib", "wldap32.lib", "winmm.lib", "ws2_32.lib",])

        if not os.path.exists(libcurl_lib_path):
            fail("libcurl.lib does not exist at %s.\nCurl directory must point to compiled libcurl (bin/include/lib subdirectories): %s" %(libcurl_lib_path, curl_dir))
        self.extra_objects.append(libcurl_lib_path)

        if scan_argv(self.argv, '--with-openssl') is not None or scan_argv(self.argv, '--with-ssl') is not None:
            self.using_openssl()

        self.check_avoid_stdio()

        # make pycurl binary work on windows xp.
        # we use inet_ntop which was added in vista and implement a fallback.
        # our implementation will not be compiled with _WIN32_WINNT targeting
        # vista or above, thus said binary won't work on xp.
        # https://curl.haxx.se/mail/curlpython-2013-12/0007.html
        self.extra_compile_args.append("-D_WIN32_WINNT=0x0501")

        if str.find(sys.version, "MSC") >= 0:
            self.extra_compile_args.append("-O2")
            self.extra_compile_args.append("-GF")        # enable read-only string pooling
            self.extra_compile_args.append("-WX")        # treat warnings as errors
            p = subprocess.Popen(['cl.exe'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()
            match = re.search(r'Version (\d+)', err.decode().split("\n")[0])
            if match and int(match.group(1)) < 16:
                # option removed in vs 2010:
                # connect.microsoft.com/VisualStudio/feedback/details/475896/link-fatal-error-lnk1117-syntax-error-in-option-opt-nowin98/
                self.extra_link_args.append("/opt:nowin98")  # use small section alignment

    if sys.platform == "win32":
        configure = configure_windows
    else:
        configure = configure_unix


    def check_avoid_stdio(self):
        if 'PYCURL_SETUP_OPTIONS' in os.environ and '--avoid-stdio' in os.environ['PYCURL_SETUP_OPTIONS']:
            self.extra_compile_args.append("-DPYCURL_AVOID_STDIO")
        if scan_argv(self.argv, '--avoid-stdio') is not None:
            self.extra_compile_args.append("-DPYCURL_AVOID_STDIO")

    def get_curl_version_info(self, dll_path):
        import ctypes

        class curl_version_info_struct(ctypes.Structure):
            _fields_ = [
                ('age', ctypes.c_int),
                ('version', ctypes.c_char_p),
                ('version_num', ctypes.c_uint),
                ('host', ctypes.c_char_p),
                ('features', ctypes.c_int),
                ('ssl_version', ctypes.c_char_p),
                ('ssl_version_num', ctypes.c_long),
                ('libz_version', ctypes.c_char_p),
                ('protocols', ctypes.c_void_p),
                ('ares', ctypes.c_char_p),
                ('ares_num', ctypes.c_int),
                ('libidn', ctypes.c_char_p),
                ('iconv_ver_num', ctypes.c_int),
                ('libssh_version', ctypes.c_char_p),
                ('brotli_ver_num', ctypes.c_uint),
                ('brotli_version', ctypes.c_char_p),
                ('nghttp2_ver_num', ctypes.c_uint),
                ('nghttp2_version', ctypes.c_char_p),
                ('quic_version', ctypes.c_char_p),
                ('cainfo', ctypes.c_char_p),
                ('capath', ctypes.c_char_p),
                ('zstd_ver_num', ctypes.c_uint),
                ('zstd_version', ctypes.c_char_p),
                ('hyper_version', ctypes.c_char_p),
                ('gsasl_version', ctypes.c_char_p),
            ]

        dll = ctypes.CDLL(dll_path)
        fn = dll.curl_version_info
        fn.argtypes = [ctypes.c_int]
        fn.restype = ctypes.POINTER(curl_version_info_struct)

        # current version is 3
        return fn(3)[0]

    def using_openssl(self):
        self.define_macros.append(('HAVE_CURL_OPENSSL', 1))
        if sys.platform == "win32":
            # CRYPTO_num_locks is defined in libeay32.lib
            # for openssl < 1.1.0; it is a noop for openssl >= 1.1.0
            self.extra_link_args.append(self.openssl_lib_name)
        else:
            # we also need ssl for the certificate functions
            # (SSL_CTX_get_cert_store)
            self.libraries.append('ssl')
            # the actual library that defines CRYPTO_num_locks etc.
            # is crypto, and on cygwin linking against ssl does not
            # link against crypto as of May 2014.
            # http://stackoverflow.com/questions/23687488/cant-get-pycurl-to-install-on-cygwin-missing-openssl-symbols-crypto-num-locks
            self.libraries.append('crypto')
        self.define_macros.append(('HAVE_CURL_SSL', 1))
        self.ssl_lib_detected = 'openssl'

    def using_wolfssl(self):
        self.define_macros.append(('HAVE_CURL_WOLFSSL', 1))
        self.libraries.append('wolfssl')
        self.define_macros.append(('HAVE_CURL_SSL', 1))
        self.ssl_lib_detected = 'wolfssl'

    def using_gnutls(self):
        self.define_macros.append(('HAVE_CURL_GNUTLS', 1))
        self.libraries.append('gnutls')
        self.define_macros.append(('HAVE_CURL_SSL', 1))
        self.ssl_lib_detected = 'gnutls'

    def using_nss(self):
        self.define_macros.append(('HAVE_CURL_NSS', 1))
        self.libraries.append('ssl3')
        self.define_macros.append(('HAVE_CURL_SSL', 1))
        self.ssl_lib_detected = 'nss'

    def using_mbedtls(self):
        self.define_macros.append(('HAVE_CURL_MBEDTLS', 1))
        self.libraries.append('mbedtls')
        self.define_macros.append(('HAVE_CURL_SSL', 1))
        self.ssl_lib_detected = 'mbedtls'

def get_bdist_msi_version_hack():
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

    return bdist_msi_version_hack


def strip_pycurl_options(argv):
    if sys.platform == 'win32':
        options = [
            '--curl-dir=', '--libcurl-lib-name=', '--use-libcurl-dll',
            '--avoid-stdio', '--with-openssl',
        ]
    else:
        options = ['--openssl-dir=', '--curl-config=', '--avoid-stdio']
    for option in options:
        scan_argv(argv, option)


###############################################################################

PRETTY_SSL_LIBS = {
    # setup.py may be detecting BoringSSL properly, need to test
    'openssl': 'OpenSSL/LibreSSL/BoringSSL',
    'wolfssl': 'wolfSSL',
    'gnutls': 'GnuTLS',
    'nss': 'NSS',
    'mbedtls': 'mbedTLS',
}

def get_extension(argv, split_extension_source=False):
    if split_extension_source:
        sources = [
            os.path.join("src", "docstrings.c"),
            os.path.join("src", "easy.c"),
            os.path.join("src", "easycb.c"),
            os.path.join("src", "easyinfo.c"),
            os.path.join("src", "easyopt.c"),
            os.path.join("src", "easyperform.c"),
            os.path.join("src", "module.c"),
            os.path.join("src", "multi.c"),
            os.path.join("src", "oscompat.c"),
            os.path.join("src", "pythoncompat.c"),
            os.path.join("src", "share.c"),
            os.path.join("src", "stringcompat.c"),
            os.path.join("src", "threadsupport.c"),
            os.path.join("src", "util.c"),
        ]
        depends = [
            os.path.join("src", "pycurl.h"),
        ]
    else:
        sources = [
            os.path.join("src", "allpycurl.c"),
        ]
        depends = []
    ext_config = ExtensionConfiguration(argv)

    if ext_config.ssl_lib_detected:
        print('Using SSL library: %s' % PRETTY_SSL_LIBS[ext_config.ssl_lib_detected])
    else:
        print('Not using an SSL library')

    ext = Extension(
        name=PACKAGE,
        sources=sources,
        depends=depends,
        include_dirs=ext_config.include_dirs,
        define_macros=ext_config.define_macros,
        library_dirs=ext_config.library_dirs,
        libraries=ext_config.libraries,
        runtime_library_dirs=ext_config.runtime_library_dirs,
        extra_objects=ext_config.extra_objects,
        extra_compile_args=ext_config.extra_compile_args,
        extra_link_args=ext_config.extra_link_args,
    )
    ##print(ext.__dict__); sys.exit(1)
    return ext


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
    files = ["AUTHORS", "ChangeLog", "COPYING-LGPL", "COPYING-MIT",
        "INSTALL.rst", "README.rst", "RELEASE-NOTES.rst"]
    if files:
        data_files.append((os.path.join(datadir), files))
    files = glob.glob(os.path.join("examples", "*.py"))
    if files:
        data_files.append((os.path.join(datadir, "examples"), files))
    files = glob.glob(os.path.join("examples", "quickstart", "*.py"))
    if files:
        data_files.append((os.path.join(datadir, "examples", "quickstart"), files))
    #
    assert data_files
    for install_dir, files in data_files:
        assert files
        for f in files:
            assert os.path.isfile(f), (f, install_dir)
    return data_files


###############################################################################

def check_manifest():
    import fnmatch

    f = open('MANIFEST.in')
    globs = []
    try:
        for line in f.readlines():
            stripped = line.strip()
            if stripped == '' or stripped.startswith('#'):
                continue
            assert stripped.startswith('include ')
            glob = stripped[8:]
            globs.append(glob)
    finally:
        f.close()

    paths = []
    start = os.path.abspath(os.path.dirname(__file__))
    for root, dirs, files in os.walk(start):
        if '.git' in dirs:
            dirs.remove('.git')
        for file in files:
            if file.endswith('.pyc'):
                continue
            rel = os.path.join(root, file)[len(start)+1:]
            paths.append(rel)

    for path in paths:
        included = False
        for glob in globs:
            if fnmatch.fnmatch(path, glob):
                included = True
                break
        if not included:
            print(path)

AUTHORS_PARAGRAPH = 3

def check_authors():
    f = open('AUTHORS')
    try:
        contents = f.read()
    finally:
        f.close()

    paras = contents.split("\n\n")
    authors_para = paras[AUTHORS_PARAGRAPH]
    authors = [author for author in authors_para.strip().split("\n")]

    log = subprocess.check_output(['git', 'log', '--format=%an (%ae)'])
    for author in log.strip().split("\n"):
        author = author.replace('@', ' at ').replace('(', '<').replace(')', '>')
        if author not in authors:
            authors.append(author)
    authors.sort()
    paras[AUTHORS_PARAGRAPH] = "\n".join(authors)
    f = open('AUTHORS', 'w')
    try:
        f.write("\n\n".join(paras))
    finally:
        f.close()


def convert_docstrings():
    docstrings = []
    for entry in sorted(os.listdir('doc/docstrings')):
        if not entry.endswith('.rst'):
            continue

        name = entry.replace('.rst', '')
        f = open('doc/docstrings/%s' % entry)
        try:
            text = f.read().strip()
        finally:
            f.close()
        docstrings.append((name, text))
    f = open('src/docstrings.c', 'w')
    try:
        f.write("/* Generated file - do not edit. */\n")
        # space to avoid having /* inside a C comment
        f.write("/* See doc/docstrings/ *.rst. */\n\n")
        f.write("#include \"pycurl.h\"\n\n")
        for name, text in docstrings:
            text = text.replace("\"", "\\\"").replace("\n", "\\n\\\n")
            f.write("PYCURL_INTERNAL const char %s_doc[] = \"%s\";\n\n" % (name, text))
    finally:
        f.close()
    f = open('src/docstrings.h', 'w')
    try:
        f.write("/* Generated file - do not edit. */\n")
        # space to avoid having /* inside a C comment
        f.write("/* See doc/docstrings/ *.rst. */\n\n")
        for name, text in docstrings:
            f.write("extern const char %s_doc[];\n" % name)
    finally:
        f.close()


def gen_docstrings_sources():
    sources = 'DOCSTRINGS_SOURCES ='
    for entry in sorted(os.listdir('doc/docstrings')):
        if entry.endswith('.rst'):
            sources += " \\\n\tdoc/docstrings/%s" % entry
    print(sources)

###############################################################################

setup_args = dict(
    name=PACKAGE,
    version=VERSION,
    description='PycURL -- A Python Interface To The cURL library',
    long_description='''\
PycURL -- A Python Interface To The cURL library
================================================

PycURL is a Python interface to `libcurl`_, the multiprotocol file
transfer library. Similarly to the urllib_ Python module,
PycURL can be used to fetch objects identified by a URL from a Python program.
Beyond simple fetches however PycURL exposes most of the functionality of
libcurl, including:

- Speed - libcurl is very fast and PycURL, being a thin wrapper above
  libcurl, is very fast as well. PycURL `was benchmarked`_ to be several
  times faster than requests_.
- Features including multiple protocol support, SSL, authentication and
  proxy options. PycURL supports most of libcurl's callbacks.
- Multi_ and share_ interfaces.
- Sockets used for network operations, permitting integration of PycURL
  into the application's I/O loop (e.g., using Tornado_).

.. _was benchmarked: http://stackoverflow.com/questions/15461995/python-requests-vs-pycurl-performance
.. _requests: http://python-requests.org/
.. _Multi: https://curl.haxx.se/libcurl/c/libcurl-multi.html
.. _share: https://curl.haxx.se/libcurl/c/libcurl-share.html
.. _Tornado: http://www.tornadoweb.org/


Requirements
------------

- Python 3.5-3.9.
- libcurl 7.19.0 or better.


Installation
------------

Download the source distribution from `PyPI`_.

Please see `the installation documentation`_ for installation instructions.

.. _PyPI: https://pypi.python.org/pypi/pycurl
.. _the installation documentation: http://pycurl.io/docs/latest/install.html


Documentation
-------------

Documentation for the most recent PycURL release is available on
`PycURL website <http://pycurl.io/docs/latest/>`_.


Support
-------

For support questions please use `curl-and-python mailing list`_.
`Mailing list archives`_ are available for your perusal as well.

Although not an official support venue, `Stack Overflow`_ has been
popular with some PycURL users.

Bugs can be reported `via GitHub`_. Please use GitHub only for bug
reports and direct questions to our mailing list instead.

.. _curl-and-python mailing list: http://cool.haxx.se/mailman/listinfo/curl-and-python
.. _Stack Overflow: http://stackoverflow.com/questions/tagged/pycurl
.. _Mailing list archives: https://curl.haxx.se/mail/list.cgi?list=curl-and-python
.. _via GitHub: https://github.com/pycurl/pycurl/issues


License
-------

PycURL is dual licensed under the LGPL and an MIT/X derivative license
based on the libcurl license. The complete text of the licenses is available
in COPYING-LGPL_ and COPYING-MIT_ files in the source distribution.

.. _libcurl: https://curl.haxx.se/libcurl/
.. _urllib: http://docs.python.org/library/urllib.html
.. _COPYING-LGPL: https://raw.githubusercontent.com/pycurl/pycurl/master/COPYING-LGPL
.. _COPYING-MIT: https://raw.githubusercontent.com/pycurl/pycurl/master/COPYING-MIT
''',
    author="Kjetil Jacobsen, Markus F.X.J. Oberhumer, Oleg Pudeyev",
    author_email="kjetilja@gmail.com, markus@oberhumer.com, oleg@bsdpower.com",
    maintainer="Oleg Pudeyev",
    maintainer_email="oleg@bsdpower.com",
    url="http://pycurl.io/",
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
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Internet :: File Transfer Protocol (FTP)',
        'Topic :: Internet :: WWW/HTTP',
    ],
    packages=[PY_PACKAGE],
    package_dir={ PY_PACKAGE: os.path.join('python', 'curl') },
    python_requires='>=3.5',
)

if sys.platform == "win32":
    setup_args['cmdclass'] = {'bdist_msi': get_bdist_msi_version_hack()}

##print distutils.__version__
if LooseVersion(distutils.__version__) > LooseVersion("1.0.1"):
    setup_args["platforms"] = "All"
if LooseVersion(distutils.__version__) < LooseVersion("1.0.3"):
    setup_args["licence"] = setup_args["license"]

unix_help = '''\
PycURL Unix options:
 --curl-config=/path/to/curl-config  use specified curl-config binary
 --libcurl-dll=[/path/to/]libcurl.so obtain SSL library from libcurl.so
 --openssl-dir=/path/to/openssl/dir  path to OpenSSL/LibreSSL/BoringSSL headers and libraries
 --with-openssl                      libcurl is linked against OpenSSL/LibreSSL/BoringSSL
 --with-ssl                          legacy alias for --with-openssl
 --with-gnutls                       libcurl is linked against GnuTLS
 --with-nss                          libcurl is linked against NSS
 --with-mbedtls                      libcurl is linked against mbedTLS
 --with-wolfssl                      libcurl is linked against wolfSSL
'''

windows_help = '''\
PycURL Windows options:
 --curl-dir=/path/to/compiled/libcurl  path to libcurl headers and libraries
 --use-libcurl-dll                     link against libcurl DLL, if not given
                                       link against libcurl statically
 --libcurl-lib-name=libcurl_imp.lib    override libcurl import library name
 --with-openssl                        libcurl is linked against OpenSSL/LibreSSL/BoringSSL
 --with-ssl                            legacy alias for --with-openssl
 --link-arg=foo.lib                    also link against specified library
'''

if __name__ == "__main__":
    if '--help' in sys.argv or '-h' in sys.argv:
        # unfortunately this help precedes distutils help
        if sys.platform == "win32":
            print(windows_help)
        else:
            print(unix_help)
        # invoke setup without configuring pycurl because
        # configuration might fail, and we want to display help anyway.
        # we need to remove our options because distutils complains about them
        strip_pycurl_options(sys.argv)
        setup(**setup_args)
    elif len(sys.argv) > 1 and sys.argv[1] == 'manifest':
        check_manifest()
    elif len(sys.argv) > 1 and sys.argv[1] == 'docstrings':
        convert_docstrings()
    elif len(sys.argv) > 1 and sys.argv[1] == 'authors':
        check_authors()
    elif len(sys.argv) > 1 and sys.argv[1] == 'docstrings-sources':
        gen_docstrings_sources()
    else:
        convert_docstrings()

        setup_args['data_files'] = get_data_files()
        if 'PYCURL_RELEASE' in os.environ and os.environ['PYCURL_RELEASE'].lower() in ['1', 'yes', 'true']:
            split_extension_source = False
        else:
            split_extension_source = True
        ext = get_extension(sys.argv, split_extension_source=split_extension_source)
        setup_args['ext_modules'] = [ext]

        for o in ext.extra_objects:
            assert os.path.isfile(o), o
        setup(**setup_args)
