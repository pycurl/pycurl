#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

"""Setup script for the PycURL module distribution."""

PACKAGE = "pycurl"
PY_PACKAGE = "curl"
VERSION = "7.19.5.1"

import glob, os, re, sys, string, subprocess
import distutils
from distutils.core import setup
from distutils.extension import Extension
from distutils.util import split_quoted
from distutils.version import LooseVersion

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


def scan_argv(s, default=None):
    p = default
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if str.find(arg, s) == 0:
            if s.endswith('='):
                # --option=value
                p = arg[len(s):]
                assert p, arg
            else:
                # --option
                # set value to True
                p = True
            del sys.argv[i]
        else:
            i = i + 1
    ##print sys.argv
    return p


class ExtensionConfiguration(object):
    def __init__(self):
        self.include_dirs = []
        self.define_macros = [("PYCURL_VERSION", '"%s"' % VERSION)]
        self.library_dirs = []
        self.libraries = []
        self.runtime_library_dirs = []
        self.extra_objects = []
        self.extra_compile_args = []
        self.extra_link_args = []
        
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
                if not dir in library_dirs:
                    self.library_dirs.append(dir)
            elif fatal:
                fail("FATAL: bad directory %s in environment variable %s" % (dir, envvar))


    def configure_unix(self):
        OPENSSL_DIR = scan_argv("--openssl-dir=")
        if OPENSSL_DIR is not None:
            self.include_dirs.append(os.path.join(OPENSSL_DIR, "include"))
        CURL_CONFIG = os.environ.get('PYCURL_CURL_CONFIG', "curl-config")
        CURL_CONFIG = scan_argv("--curl-config=", CURL_CONFIG)
        try:
            p = subprocess.Popen((CURL_CONFIG, '--version'),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError:
            exc = sys.exc_info()[1]
            msg = 'Could not run curl-config: %s' % str(exc)
            raise ConfigurationError(msg)
        stdout, stderr = p.communicate()
        if p.wait() != 0:
            msg = "`%s' not found -- please install the libcurl development files or specify --curl-config=/path/to/curl-config" % CURL_CONFIG
            if stderr:
                msg += ":\n" + stderr.decode()
            raise ConfigurationError(msg)
        libcurl_version = stdout.decode().strip()
        print("Using %s (%s)" % (CURL_CONFIG, libcurl_version))
        p = subprocess.Popen((CURL_CONFIG, '--cflags'),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if p.wait() != 0:
            msg = "Problem running `%s' --cflags" % CURL_CONFIG
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
            p = subprocess.Popen((CURL_CONFIG, option),
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
        
        ssl_lib_detected = False
        if 'PYCURL_SSL_LIBRARY' in os.environ:
            ssl_lib = os.environ['PYCURL_SSL_LIBRARY']
            if ssl_lib in ['openssl', 'gnutls', 'nss']:
                ssl_lib_detected = True
                self.define_macros.append(('HAVE_CURL_%s' % ssl_lib.upper(), 1))
            else:
                raise ConfigurationError('Invalid value "%s" for PYCURL_SSL_LIBRARY' % ssl_lib)
        ssl_options = {
            '--with-ssl': 'HAVE_CURL_OPENSSL',
            '--with-gnutls': 'HAVE_CURL_GNUTLS',
            '--with-nss': 'HAVE_CURL_NSS',
        }
        for option in ssl_options:
            if scan_argv(option) is not None:
                for other_option in ssl_options:
                    if option != other_option:
                        if scan_argv(other_option) is not None:
                            raise ConfigurationError('Cannot give both %s and %s' % (option, other_option))
                ssl_lib_detected = True
                self.define_macros.append((ssl_options[option], 1))

        # libraries and options - all libraries and options are forwarded
        # but if --libs succeeded, --static-libs output is ignored
        for arg in split_quoted(optbuf):
            if arg[:2] == "-l":
                self.libraries.append(arg[2:])
            elif arg[:2] == "-L":
                self.library_dirs.append(arg[2:])
            else:
                self.extra_link_args.append(arg)
        # ssl detection - ssl libraries are forwarded
        for arg in split_quoted(sslhintbuf):
            if arg[:2] == "-l":
                if not ssl_lib_detected and arg[2:] == 'ssl':
                    self.define_macros.append(('HAVE_CURL_OPENSSL', 1))
                    ssl_lib_detected = True
                    # the actual library that defines CRYPTO_num_locks etc.
                    # is crypto, and on cygwin linking against ssl does not
                    # link against crypto as of May 2014.
                    # http://stackoverflow.com/questions/23687488/cant-get-pycurl-to-install-on-cygwin-missing-openssl-symbols-crypto-num-locks
                    self.libraries.append('crypto')
                if not ssl_lib_detected and arg[2:] == 'gnutls':
                    self.define_macros.append(('HAVE_CURL_GNUTLS', 1))
                    ssl_lib_detected = True
                    self.libraries.append('gnutls')
                if not ssl_lib_detected and arg[2:] == 'ssl3':
                    self.define_macros.append(('HAVE_CURL_NSS', 1))
                    ssl_lib_detected = True
                    self.libraries.append('ssl3')
        if not ssl_lib_detected:
            p = subprocess.Popen((CURL_CONFIG, '--features'),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = p.communicate()
            if p.wait() != 0:
                msg = "Problem running `%s' --features" % CURL_CONFIG
                if stderr:
                    msg += ":\n" + stderr.decode()
                raise ConfigurationError(msg)
            for feature in split_quoted(stdout.decode()):
                if feature == 'SSL':
                    # this means any ssl library, not just openssl
                    self.define_macros.append(('HAVE_CURL_SSL', 1))
        else:
            # if we are configuring for a particular ssl library,
            # we can assume that ssl is being used
            self.define_macros.append(('HAVE_CURL_SSL', 1))
        if not self.libraries:
            self.libraries.append("curl")
        
        # Add extra compile flag for MacOS X
        if sys.platform[:-1] == "darwin":
            self.extra_link_args.append("-flat_namespace")
        
        # Recognize --avoid-stdio on Unix so that it can be tested
        self.check_avoid_stdio()


    def configure_windows(self):
        # Windows users have to pass --curl-dir parameter to specify path
        # to libcurl, because there is no curl-config on windows at all.
        curl_dir = scan_argv("--curl-dir=")
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
        # in practice, the library name sometimes is libcurl.lib.
        # override with: --libcurl-lib-name=libcurl_imp.lib
        curl_lib_name = scan_argv('--libcurl-lib-name=', 'libcurl.lib')

        if scan_argv("--use-libcurl-dll") is not None:
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
        
        self.check_avoid_stdio()
        
        # make pycurl binary work on windows xp.
        # we use inet_ntop which was added in vista and implement a fallback.
        # our implementation will not be compiled with _WIN32_WINNT targeting
        # vista or above, thus said binary won't work on xp.
        # http://curl.haxx.se/mail/curlpython-2013-12/0007.html
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
        if scan_argv('--avoid-stdio') is not None:
            self.extra_compile_args.append("-DPYCURL_AVOID_STDIO")

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


def strip_pycurl_options():
    if sys.platform == 'win32':
        options = [
            '--curl-dir=', '--curl-lib-name=', '--use-libcurl-dll',
            '--avoid-stdio',
        ]
    else:
        options = ['--openssl-dir=', '--curl-config=', '--avoid-stdio']
    for option in options:
        scan_argv(option)


###############################################################################

def get_extension(split_extension_source=False):
    if split_extension_source:
        sources = [
            os.path.join("src", "docstrings.c"),
            os.path.join("src", "easy.c"),
            os.path.join("src", "module.c"),
            os.path.join("src", "multi.c"),
            os.path.join("src", "oscompat.c"),
            os.path.join("src", "pythoncompat.c"),
            os.path.join("src", "share.c"),
            os.path.join("src", "stringcompat.c"),
            os.path.join("src", "threadsupport.c"),
        ]
        depends = [
            os.path.join("src", "pycurl.h"),
        ]
    else:
        sources = [
            os.path.join("src", "allpycurl.c"),
        ]
        depends = []
    ext_config = ExtensionConfiguration()
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
    description="PycURL -- cURL library module for Python",
    author="Kjetil Jacobsen, Markus F.X.J. Oberhumer, Oleg Pudeyev",
    author_email="kjetilja at gmail.com, markus at oberhumer.com, oleg at bsdpower.com",
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
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: File Transfer Protocol (FTP)',
        'Topic :: Internet :: WWW/HTTP',
    ],
    packages=[PY_PACKAGE],
    package_dir={ PY_PACKAGE: os.path.join('python', 'curl') },
    long_description="""
This module provides Python bindings for the cURL library.""",
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
 --openssl-dir=/path/to/openssl/dir  path to OpenSSL headers and libraries
 --with-ssl                          libcurl is linked against OpenSSL
 --with-gnutls                       libcurl is linked against GnuTLS
 --with-nss                          libcurl is linked against NSS
'''

windows_help = '''\
PycURL Windows options:
 --curl-dir=/path/to/compiled/libcurl  path to libcurl headers and libraries
 --use-libcurl-dll                     link against libcurl DLL, if not given
                                       link against libcurl statically
 --libcurl-lib-name=libcurl_imp.lib    override libcurl import library name
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
        strip_pycurl_options()
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
        setup_args['data_files'] = get_data_files()
        if 'PYCURL_RELEASE' in os.environ and os.environ['PYCURL_RELEASE'].lower() in ['1', 'yes', 'true']:
            split_extension_source = False
        else:
            split_extension_source = True
        ext = get_extension(split_extension_source=split_extension_source)
        setup_args['ext_modules'] = [ext]
        
        for o in ext.extra_objects:
            assert os.path.isfile(o), o
        setup(**setup_args)
