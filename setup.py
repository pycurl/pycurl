"""Setup script for the PycURL module distribution."""

EXTENSION_NAME = "pycurl._pycurl"
VERSION = "7.48.0"

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from setuptools import setup
from setuptools.command.build_ext import build_ext as _build_ext
from setuptools.extension import Extension

class ConfigurationError(Exception):
    pass


def fail(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(10)


class ExtensionConfiguration:
    def __init__(self):
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
        for feature in shlex.split(stdout.decode()):
            if feature == 'SSL':
                # this means any ssl library, not just openssl.
                # we set the ssl flag to check for ssl library mismatch
                # at link time and run time
                self.define_macros.append(('HAVE_CURL_SSL', 1))
                curl_has_ssl = True
        self.curl_has_ssl = curl_has_ssl

    def detect_ssl_backend(self):
        ssl_lib_detected = None

        if 'PYCURL_SSL_LIBRARY' in os.environ:
            ssl_lib = os.environ['PYCURL_SSL_LIBRARY']
            if ssl_lib in ['openssl', 'wolfssl', 'gnutls', 'nss', 'mbedtls', 'sectransp']:
                ssl_lib_detected = ssl_lib
                getattr(self, 'using_%s' % ssl_lib)()
            else:
                raise ConfigurationError('Invalid value "%s" for PYCURL_SSL_LIBRARY' % ssl_lib)

        if not ssl_lib_detected:
            libcurl_dll_path = os.environ.get('PYCURL_LIBCURL_DLL')
            if libcurl_dll_path is not None:
                ssl_lib_detected = self.detect_ssl_lib_from_libcurl_dll(libcurl_dll_path)

        if not ssl_lib_detected:
            ssl_lib_detected = self.detect_ssl_lib_using_curl_config()

        if not ssl_lib_detected:
            # self.sslhintbuf is a hack
            for arg in shlex.split(self.sslhintbuf):
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

        self.ssl_lib_detected = ssl_lib_detected

    def curl_config(self):
        try:
            return self._curl_config
        except AttributeError:
            curl_config = os.environ.get('PYCURL_CURL_CONFIG', "curl-config")
            self._curl_config = curl_config
            return curl_config

    def configure_unix(self):
        OPENSSL_DIR = os.environ.get('PYCURL_OPENSSL_DIR')
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
            msg = "`%s' not found -- please install the libcurl development files or set the PYCURL_CURL_CONFIG environment variable to the path to curl-config" % self.curl_config()
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
        for arg in shlex.split(stdout.decode()):
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
        # The final point is we should link against the SSL library in use
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
OpenSSL, LibreSSL, BoringSSL, GnuTLS, NSS, mbedTLS, or Secure Transport \
please specify the SSL backend manually. For other SSL backends please \
ignore this message.''')
        else:
            if 'PYCURL_SSL_LIBRARY' in os.environ:
                sys.stderr.write("Warning: SSL backend specified manually but libcurl does not use SSL\n")

        # libraries and options - all libraries and options are forwarded
        # but if --libs succeeded, --static-libs output is ignored
        for arg in shlex.split(optbuf):
            if arg[:2] == "-l":
                self.libraries.append(arg[2:])
            elif arg[:2] == "-L":
                self.library_dirs.append(arg[2:])
            else:
                self.extra_link_args.append(arg)

        if not self.libraries:
            self.libraries.append("curl")

        self.check_werror()

        try:
            for dir in os.environ['PYCURL_RUNTIME_LIBRARY_DIRS'].split(os.pathsep):
                self.runtime_library_dirs.append(dir)
        except KeyError:
            pass

        try:
            for obj in os.environ['PYCURL_EXTRA_OBJECTS'].split(os.pathsep):
                self.extra_objects.append(obj)
        except KeyError:
            pass

        try:
            for obj in os.environ['PYCURL_EXTRA_LIBRARIES'].split(os.pathsep):
                self.libraries.append(obj)
        except KeyError:
            pass

        if 'PYCURL_AUTODETECT_CA' in os.environ:
            self.extra_compile_args.append("-DPYCURL_AUTODETECT_CA")

    def detect_ssl_lib_from_libcurl_dll(self, libcurl_dll_path):
        ssl_lib_detected = None
        curl_version_info = self.get_curl_version_info(libcurl_dll_path)
        ssl_version = curl_version_info.ssl_version
        # ssl_version is bytes, decode to string
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
        elif ssl_version.startswith('SecureTransport'):
            self.using_sectransp()
            ssl_lib_detected = 'sectransp'
        return ssl_lib_detected

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
        OPENSSL_DIR = os.environ.get('PYCURL_OPENSSL_DIR')
        if OPENSSL_DIR is not None:
            self.include_dirs.append(os.path.join(OPENSSL_DIR, "include"))
            self.library_dirs.append(os.path.join(OPENSSL_DIR, "lib"))
        # Windows users have to set PYCURL_CURL_DIR to specify path
        # to libcurl, because there is no curl-config on windows at all.
        curl_dir = os.environ.get('PYCURL_CURL_DIR')
        if curl_dir is None:
            fail("Please set the PYCURL_CURL_DIR environment variable to the path to built libcurl")
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
        # override with: PYCURL_LIBCURL_LIB_NAME=libcurl_imp.lib
        curl_lib_name = os.environ.get('PYCURL_LIBCURL_LIB_NAME', 'libcurl.lib')

        # OpenSSL 1.1.0 renamed its import libraries from
        # libeay32.lib/ssleay32.lib to libcrypto.lib/libssl.lib, and dropped
        # the thread locking callback interface at the same time, meaning we
        # do not need to link against an OpenSSL import library at all by
        # default. Override with PYCURL_OPENSSL_LIB_NAME if yours does.
        self.openssl_lib_name = os.environ.get('PYCURL_OPENSSL_LIB_NAME', '')

        try:
            for lib in os.environ['PYCURL_LINK_ARG'].split(os.pathsep):
                self.extra_link_args.append(lib)
        except KeyError:
            pass

        if os.environ.get('PYCURL_USE_LIBCURL_DLL') is not None:
            libcurl_lib_path = os.path.join(curl_dir, "lib", curl_lib_name)
            self.extra_link_args.extend(["ws2_32.lib"])
            if "MSC" in sys.version:
                # build a dll
                self.extra_compile_args.append("-MD")
        else:
            self.extra_compile_args.append("-DCURL_STATICLIB")
            libcurl_lib_path = os.path.join(curl_dir, "lib", curl_lib_name)
            self.extra_link_args.extend(["gdi32.lib", "wldap32.lib", "winmm.lib", "ws2_32.lib",])

        if not os.path.exists(libcurl_lib_path):
            fail("libcurl.lib does not exist at %s.\nCurl directory must point to compiled libcurl (bin/include/lib subdirectories): %s" %(libcurl_lib_path, curl_dir))
        self.extra_objects.append(libcurl_lib_path)

        if 'PYCURL_SSL_LIBRARY' in os.environ:
            ssl_lib = os.environ['PYCURL_SSL_LIBRARY']
            if ssl_lib in ['openssl', 'schannel']:
                getattr(self, 'using_%s' % ssl_lib)()
            else:
                raise ConfigurationError('Invalid value "%s" for PYCURL_SSL_LIBRARY' % ssl_lib)

        if "MSC" in sys.version:
            self.extra_compile_args.append("-O2")
            self.extra_compile_args.append("-GF")        # enable read-only string pooling
            self.extra_compile_args.append("-WX")        # treat warnings as errors

    if sys.platform == "win32":
        configure = configure_windows
    else:
        configure = configure_unix


    def check_werror(self):
        # Not CFLAGS, which unrelated builds (e.g. vcpkg) in the same environment also pick up.
        if os.environ.get('PYCURL_WERROR'):
            self.extra_compile_args.append("-Werror")

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
            # CRYPTO_num_locks was defined in libeay32.lib for openssl <
            # 1.1.0; not needed for 1.1.0+, which is why the default is empty.
            if self.openssl_lib_name:
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

    def using_sectransp(self):
        self.define_macros.append(('HAVE_CURL_SECTRANSP', 1))
        self.define_macros.append(('HAVE_CURL_SSL', 1))
        self.ssl_lib_detected = 'sectransp'

    def using_schannel(self):
        self.define_macros.append(('HAVE_CURL_SCHANNEL', 1))
        self.define_macros.append(('HAVE_CURL_SSL', 1))
        self.ssl_lib_detected = 'schannel'


###############################################################################

PRETTY_SSL_LIBS = {
    # setup.py may be detecting BoringSSL properly, need to test
    'openssl': 'OpenSSL/LibreSSL/BoringSSL',
    'wolfssl': 'wolfSSL',
    'gnutls': 'GnuTLS',
    'nss': 'NSS',
    'mbedtls': 'mbedTLS',
    'sectransp': 'Secure Transport',
    'schannel': 'Schannel',
}

def get_extension():
    sources = [
        os.path.join("src", "docstrings.c"),
        os.path.join("src", "easy.c"),
        os.path.join("src", "easycb.c"),
        os.path.join("src", "easyinfo.c"),
        os.path.join("src", "easyopt.c"),
        os.path.join("src", "easyperform.c"),
        os.path.join("src", "easyws.c"),
        os.path.join("src", "module.c"),
        os.path.join("src", "mime.c"),
        os.path.join("src", "multi.c"),
        os.path.join("src", "oscompat.c"),
        os.path.join("src", "pythoncompat.c"),
        os.path.join("src", "share.c"),
        os.path.join("src", "stringcompat.c"),
        os.path.join("src", "threadsupport.c"),
        os.path.join("src", "url.c"),
        os.path.join("src", "util.c"),
    ]
    depends = [
        os.path.join("src", "pycurl.h"),
    ]
    return Extension(name=EXTENSION_NAME, sources=sources, depends=depends)


class BuildExt(_build_ext):
    def run(self):
        generate_docstrings()

        config = ExtensionConfiguration()
        if config.ssl_lib_detected:
            print('Using SSL library: %s' % PRETTY_SSL_LIBS[config.ssl_lib_detected])
        else:
            print('Not using an SSL library')

        for ext in self.extensions:
            if ext.name != EXTENSION_NAME:
                continue
            ext.include_dirs.extend(config.include_dirs)
            ext.define_macros.extend(config.define_macros)
            ext.library_dirs.extend(config.library_dirs)
            ext.libraries.extend(config.libraries)
            ext.runtime_library_dirs.extend(config.runtime_library_dirs)
            ext.extra_objects.extend(config.extra_objects)
            ext.extra_compile_args.extend(config.extra_compile_args)
            ext.extra_link_args.extend(config.extra_link_args)
            for o in ext.extra_objects:
                assert os.path.isfile(o), o

        super().run()


###############################################################################

def generate_docstrings():
    docstrings_dir = Path("doc", "docstrings")
    docstrings = [
        (entry.stem, entry.read_text(encoding="utf-8").strip())
        for entry in sorted(docstrings_dir.glob("*.rst"))
    ]

    with Path("src", "docstrings.c").open("w", encoding="utf-8") as f:
        f.write("/* Generated file - do not edit. */\n")
        # space to avoid having /* inside a C comment
        f.write("/* See doc/docstrings/ *.rst. */\n\n")
        f.write("#include \"pycurl.h\"\n\n")
        for name, text in docstrings:
            text = text.replace("\"", "\\\"").replace("\n", "\\n\\\n")
            f.write("PYCURL_INTERNAL const char %s_doc[] = \"%s\";\n\n" % (name, text))

    with Path("src", "docstrings.h").open("w", encoding="utf-8") as f:
        f.write("/* Generated file - do not edit. */\n")
        # space to avoid having /* inside a C comment
        f.write("/* See doc/docstrings/ *.rst. */\n\n")
        for name, text in docstrings:
            f.write("extern const char %s_doc[];\n" % name)

###############################################################################

setup_args = dict(
    version=VERSION,
    ext_modules=[get_extension()],
    cmdclass={'build_ext': BuildExt},
)

if __name__ == "__main__":
    setup(**setup_args)
