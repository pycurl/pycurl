# Bootstrap python binary:
# http://www.python.org/ftp/python/3.3.4/python-3.3.4.msi
# http://www.python.org/ftp/python/3.3.4/python-3.3.4.amd64.msi
# msvc9/vs2008 express:
# http://go.microsoft.com/?linkid=7729279
# msvc10/vs2010 express:
# http://go.microsoft.com/?linkid=9709949
# for 64 bit builds, then install 2010 sp1:
# http://go.microsoft.com/fwlink/?LinkId=210710
# ... and windows 7 sdk (because sp1 compiler update refuses to install
# without it):
# http://www.microsoft.com/en-us/download/details.aspx?id=8279
# or http://www.microsoft.com/en-us/download/details.aspx?id=8442
# then install sp1 compiler update:
# https://www.microsoft.com/en-us/download/details.aspx?id=4422
# msvc14/vs2015 community:
# https://www.visualstudio.com/en-us/downloads/download-visual-studio-vs.aspx
#
# OpenSSL build resources including 64-bit builds:
# http://stackoverflow.com/questions/158232/how-do-you-compile-openssl-for-x64
# https://wiki.openssl.org/index.php/Compilation_and_Installation
# http://developer.covenanteyes.com/building-openssl-for-visual-studio/
#
# NASM:
# http://www.nasm.us/
# ActiveState Perl:
# http://www.activestate.com/activeperl/downloads

# work directory for downloading dependencies and building everything
root = 'c:/dev/build-pycurl'
# where msysgit is installed
git_root = 'c:/program files/git'
# where NASM is installed, for building OpenSSL
nasm_path = ('c:/dev/nasm', 'c:/program files (x86)/nasm')
# where ActiveState Perl is installed, for building 64-bit OpenSSL
activestate_perl_path = r'c:\dev\perl64'
# which versions of python to build against
python_versions = ['2.6.6', '2.7.10', '3.2.5', '3.3.5', '3.4.3', '3.5.4', '3.6.2']
# where pythons are installed
python_path_template = 'c:/dev/%(bitness)s/python%(python_release)s/python'
vc_paths = {
    # where msvc 9/vs 2008 is installed, for python 2.6 through 3.2
    'vc9': None,
    # where msvc 10/vs 2010 is installed, for python 3.3 through 3.4
    'vc10': None,
    # where msvc 14/vs 2015 is installed, for python 3.5
    'vc14': None,
}
# whether to link libcurl against zlib
use_zlib = True
# which version of zlib to use, will be downloaded from internet
zlib_version = '1.2.11'
# whether to use openssl instead of winssl
use_openssl = True
# which version of openssl to use, will be downloaded from internet
openssl_version = '1.1.0f'
# whether to use c-ares
use_cares = True
cares_version = '1.13.0'
# whether to use libssh2
use_libssh2 = True
libssh2_version = '1.8.0'
# which version of libcurl to use, will be downloaded from internet
libcurl_version = '7.55.1'
# virtualenv version
virtualenv_version = '15.1.0'
# whether to build binary wheels
build_wheels = True
# pycurl version to build, we should know this ourselves
pycurl_version = '7.43.0.1'

default_vc_paths = {
    # where msvc 9 is installed, for python 2.6 through 3.2
    'vc9': [
        'c:/program files (x86)/microsoft visual studio 9.0',
        'c:/program files/microsoft visual studio 9.0',
    ],
    # where msvc 10 is installed, for python 3.3 through 3.4
    'vc10': [
        'c:/program files (x86)/microsoft visual studio 10.0',
        'c:/program files/microsoft visual studio 10.0',
    ],
    # where msvc 14 is installed, for python 3.5
    'vc14': [
        'c:/program files (x86)/microsoft visual studio 14.0',
        'c:/program files/microsoft visual studio 14.0',
    ],
}

def short_python_versions(python_versions):
    return ['.'.join(python_version.split('.')[:2])
        for python_version in python_versions]

def needed_vc_versions(python_versions):
    return [vc_version for vc_version in vc_paths.keys()
        if vc_version in [
            python_vc_versions[short_python_version]
            for short_python_version in short_python_versions(python_versions)]]

import os, os.path, sys, subprocess, shutil, contextlib, zipfile, re

archives_path = os.path.join(root, 'archives')
state_path = os.path.join(root, 'state')
#git_bin_path = os.path.join(git_root, 'bin')
git_bin_path = ''
git_path = os.path.join(git_bin_path, 'git')
rm_path = os.path.join(git_bin_path, 'rm')
tar_path = os.path.join(git_bin_path, 'tar')
activestate_perl_bin_path = os.path.join(activestate_perl_path, 'bin')
python_vc_versions = {
    '2.6': 'vc9',
    '2.7': 'vc9',
    '3.2': 'vc9',
    '3.3': 'vc10',
    '3.4': 'vc10',
    '3.5': 'vc14',
    '3.6': 'vc14',
}
vc_versions = vc_paths.keys()
dir_here = os.path.abspath(os.path.dirname(__file__))

openssl_version_tuple = tuple(
    int(part) if part < 'a' else part
    for part in re.sub(r'([a-z])', r'.\1', openssl_version).split('.')
)

def select_existing_path(paths):
    if isinstance(paths, list) or isinstance(paths, tuple):
        for path in paths:
            if os.path.exists(path):
                return path
        return paths[0]
    else:
        return paths

nasm_path = select_existing_path(nasm_path)

try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen

def mkdir_p(path):
    if not os.path.exists(path):
        os.makedirs(path)

def fetch(url, archive=None):
    if archive is None:
        archive = os.path.basename(url)
    if not os.path.exists(archive):
        sys.stdout.write("Fetching %s\n" % url)
        io = urlopen(url)
        tmp_path = os.path.join(os.path.dirname(archive),
            '.%s.part' % os.path.basename(archive))
        with open(tmp_path, 'wb') as f:
            while True:
                chunk = io.read(65536)
                if len(chunk) == 0:
                    break
                f.write(chunk)
        os.rename(tmp_path, archive)

@contextlib.contextmanager
def in_dir(dir):
    old_cwd = os.getcwd()
    try:
        os.chdir(dir)
        yield
    finally:
        os.chdir(old_cwd)

@contextlib.contextmanager
def step(step_fn, args, target_dir):
    #step = step_fn.__name__
    state_tag = target_dir
    mkdir_p(state_path)
    state_file_path = os.path.join(state_path, state_tag)
    if not os.path.exists(state_file_path) or not os.path.exists(target_dir):
        step_fn(*args)
    with open(state_file_path, 'w'):
        pass

def untar(basename):
    if os.path.exists(basename):
        shutil.rmtree(basename)
    subprocess.check_call([tar_path, 'xf', '%s.tar.gz' % basename])

def rename_for_vc(basename, suffix):
    suffixed_dir = '%s-%s' % (basename, suffix)
    if os.path.exists(suffixed_dir):
        shutil.rmtree(suffixed_dir)
    os.rename(basename, suffixed_dir)
    return suffixed_dir

class PythonRelease(str):
    @property
    def dotless(self):
        return self.replace('.', '')

def python_releases():
    return [PythonRelease('.'.join(version.split('.')[:2]))
        for version in python_versions]

class PythonBinary(object):
    def __init__(self, python_release, bitness):
        self.python_release = python_release
        self.bitness = bitness

    @property
    def executable_path(self):
        return python_path_template % dict(
            python_release=self.python_release.dotless,
            bitness=self.bitness)

class Builder(object):
    def __init__(self, **kwargs):
        bitness = kwargs.pop('bitness')
        assert bitness in (32, 64)
        self.bitness = bitness
        self.vc_version = kwargs.pop('vc_version')
        self.use_dlls = False

    @property
    def vcvars_bitness_parameter(self):
        params = {
            32: 'x86',
            64: 'amd64',
        }
        return params[self.bitness]

    @property
    def vcvars_relative_path(self):
        return 'vc/vcvarsall.bat'

    @property
    def vc_path(self):
        if self.vc_version in vc_paths and vc_paths[self.vc_version]:
            path = vc_paths[self.vc_version]
            if not os.path.join(path, self.vcvars_relative_path):
                raise Exception('vcvars not found in specified path')
            return path
        else:
            for path in default_vc_paths[self.vc_version]:
                if os.path.exists(os.path.join(path, self.vcvars_relative_path)):
                    return path
            raise Exception('No usable vc path found')

    @property
    def vcvars_path(self):
        return os.path.join(self.vc_path, self.vcvars_relative_path)

    @property
    def vcvars_cmd(self):
        # https://msdn.microsoft.com/en-us/library/x4d2c09s.aspx
        return "call \"%s\" %s\n" % (
            self.vcvars_path,
            self.vcvars_bitness_parameter,
        )

    @property
    def nasm_cmd(self):
        return "set path=%s;%%path%%\n" % nasm_path

    @contextlib.contextmanager
    def execute_batch(self):
        with open('doit.bat', 'w') as f:
            f.write(self.vcvars_cmd)
            f.write(self.nasm_cmd)
            yield f
        if True:
            print("Executing:")
            with open('doit.bat', 'r') as f:
                print(f.read())
            sys.stdout.flush()
        subprocess.check_call(['doit.bat'])

    @property
    def vc_tag(self):
        return '%s-%s' % (self.vc_version, self.bitness)

class ZlibBuilder(Builder):
    def __init__(self, **kwargs):
        super(ZlibBuilder, self).__init__(**kwargs)
        self.zlib_version = kwargs.pop('zlib_version')

    @property
    def state_tag(self):
        return 'zlib-%s-%s' % (self.zlib_version, self.vc_tag)

    def build(self):
        fetch('http://downloads.sourceforge.net/project/libpng/zlib/%s/zlib-%s.tar.gz' % (self.zlib_version, self.zlib_version))
        untar('zlib-%s' % self.zlib_version)
        zlib_dir = rename_for_vc('zlib-%s' % self.zlib_version, self.vc_tag)
        with in_dir(zlib_dir):
            with self.execute_batch() as f:
                f.write("nmake /f win32/Makefile.msc\n")

    @property
    def output_dir_path(self):
        return 'zlib-%s-%s' % (self.zlib_version, self.vc_tag)

    @property
    def dll_paths(self):
        return [
            os.path.join(self.output_dir_path, 'zlib1.dll'),
        ]

    @property
    def include_path(self):
        return os.path.join(archives_path, self.output_dir_path)

    @property
    def lib_path(self):
        return os.path.join(archives_path, self.output_dir_path)

class OpensslBuilder(Builder):
    def __init__(self, **kwargs):
        super(OpensslBuilder, self).__init__(**kwargs)
        self.openssl_version = kwargs.pop('openssl_version')

    @property
    def state_tag(self):
        return 'openssl-%s-%s' % (self.openssl_version, self.vc_tag)

    def build(self):
        fetch('https://www.openssl.org/source/openssl-%s.tar.gz' % self.openssl_version)
        try:
            untar('openssl-%s' % self.openssl_version)
        except subprocess.CalledProcessError:
            # openssl tarballs include symlinks which cannot be extracted on windows,
            # and hence cause errors during extraction.
            # apparently these symlinks will be regenerated at configure stage...
            # makes one wonder why they are included in the first place.
            pass
        # another openssl gem:
        # nasm output is redirected to NUL which ends up creating a file named NUL.
        # however being a reserved file name this file is not deletable by
        # ordinary tools.
        nul_file = "openssl-%s-%s\\NUL" % (self.openssl_version, self.vc_tag)
        subprocess.check_call(['rm', '-f', nul_file])
        openssl_dir = rename_for_vc('openssl-%s' % self.openssl_version, self.vc_tag)
        with in_dir(openssl_dir):
            with self.execute_batch() as f:
                if openssl_version_tuple < (1, 1):
                    # openssl 1.0.2
                    f.write("patch -p0 < %s\n" % os.path.join(dir_here, 'winbuild', 'openssl-fix-crt-1.0.2.patch'))
                else:
                    # openssl 1.1.0
                    f.write("patch -p0 < %s\n" % os.path.join(dir_here, 'winbuild', 'openssl-fix-crt-1.1.0.patch'))
                if self.bitness == 64:
                    target = 'VC-WIN64A'
                    batch_file = 'do_win64a'
                else:
                    target = 'VC-WIN32'
                    batch_file = 'do_nasm'

                # msysgit perl has trouble with backslashes used in
                # win64 assembly things in openssl 1.0.2
                # and in x86 assembly as well in openssl 1.1.0;
                # use ActiveState Perl
                if not os.path.exists(activestate_perl_bin_path):
                    raise ValueError('activestate_perl_bin_path refers to a nonexisting path')
                if not os.path.exists(os.path.join(activestate_perl_bin_path, 'perl.exe')):
                    raise ValueError('No perl binary in activestate_perl_bin_path')
                f.write("set path=%s;%%path%%\n" % activestate_perl_bin_path)
                f.write("perl -v\n")

                openssl_prefix = os.path.join(os.path.realpath('.'), 'build')
                # Do not want compression:
                # https://en.wikipedia.org/wiki/CRIME
                extras = ['no-comp']
                if openssl_version_tuple >= (1, 1):
                    # openssl 1.1.0
                    # in 1.1.0 the static/shared selection is handled by
                    # invoking the right makefile
                    extras += ['no-shared']
                    
                    # looks like openssl 1.1.0c does not derive
                    # --openssldir from --prefix, like its Configure claims,
                    # and like 1.0.2 does; provide a relative openssl dir
                    # manually
                    extras += ['--openssldir=ssl']
                f.write("perl Configure %s %s --prefix=%s\n" % (target, ' '.join(extras), openssl_prefix))
                
                if openssl_version_tuple < (1, 1):
                    # openssl 1.0.2
                    f.write("call ms\\%s\n" % batch_file)
                    f.write("nmake -f ms\\nt.mak\n")
                    f.write("nmake -f ms\\nt.mak install\n")
                else:
                    # openssl 1.1.0
                    f.write("nmake\n")
                    f.write("nmake install\n")

    @property
    def output_dir_path(self):
        return 'openssl-%s-%s/build' % (self.openssl_version, self.vc_tag)

    @property
    def dll_paths(self):
        raise NotImplemented

    @property
    def include_path(self):
        return os.path.join(archives_path, self.output_dir_path, 'include')

    @property
    def lib_path(self):
        return os.path.join(archives_path, self.output_dir_path, 'lib')

class CaresBuilder(Builder):
    def __init__(self, **kwargs):
        super(CaresBuilder, self).__init__(**kwargs)
        self.cares_version = kwargs.pop('cares_version')

    @property
    def state_tag(self):
        return 'c-ares-%s-%s' % (self.cares_version, self.vc_tag)

    def build(self):
        fetch('http://c-ares.haxx.se/download/c-ares-%s.tar.gz' % (self.cares_version))
        untar('c-ares-%s' % self.cares_version)
        if self.cares_version == '1.12.0':
            # msvc_ver.inc is missing in c-ares-1.12.0.tar.gz
            # https://github.com/c-ares/c-ares/issues/69
            fetch('https://raw.githubusercontent.com/c-ares/c-ares/cares-1_12_0/msvc_ver.inc',
                  archive='c-ares-1.12.0/msvc_ver.inc')
        cares_dir = rename_for_vc('c-ares-%s' % self.cares_version, self.vc_tag)
        with in_dir(cares_dir):
            with self.execute_batch() as f:
                if self.cares_version == '1.10.0':
                    f.write("patch -p1 < %s\n" % os.path.join(dir_here, 'winbuild', 'c-ares-vs2015.patch'))
                f.write("nmake -f Makefile.msvc\n")

    @property
    def output_dir_path(self):
        return 'c-ares-%s-%s' % (self.cares_version, self.vc_tag)

    @property
    def dll_paths(self):
        raise NotImplemented

    @property
    def include_path(self):
        return os.path.join(archives_path, self.output_dir_path)

    @property
    def lib_path(self):
        return os.path.join(archives_path, self.output_dir_path,
            'ms%s0' % self.vc_version, 'cares', 'lib-release')

class Libssh2Builder(Builder):
    def __init__(self, **kwargs):
        super(Libssh2Builder, self).__init__(**kwargs)
        self.libssh2_version = kwargs.pop('libssh2_version')
        self.zlib_version = kwargs.pop('zlib_version')
        self.openssl_version = kwargs.pop('openssl_version')

    @property
    def state_tag(self):
        return 'libssh2-%s-%s' % (self.libssh2_version, self.vc_tag)

    def build(self):
        fetch('http://www.libssh2.org/download/libssh2-%s.tar.gz' % (self.libssh2_version))
        untar('libssh2-%s' % self.libssh2_version)
        libssh2_dir = rename_for_vc('libssh2-%s' % self.libssh2_version, self.vc_tag)
        with in_dir(libssh2_dir):
            with self.execute_batch() as f:
                if self.vc_version == 'vc14':
                    f.write("patch -p0 < %s\n" % os.path.join(dir_here, 'winbuild', 'libssh2-vs2015.patch'))
                zlib_builder = ZlibBuilder(bitness=self.bitness, vc_version=self.vc_version, zlib_version=self.zlib_version)
                openssl_builder = OpensslBuilder(bitness=self.bitness, vc_version=self.vc_version, openssl_version=self.openssl_version)
                vars = '''
OPENSSLINC=%(openssl_include_path)s
OPENSSLLIB=%(openssl_lib_path)s
ZLIBINC=%(zlib_include_path)s
ZLIBLIB=%(zlib_lib_path)s
WITH_ZLIB=1
BUILD_STATIC_LIB=1
                ''' % dict(
                    openssl_include_path=openssl_builder.include_path,
                    openssl_lib_path=openssl_builder.lib_path,
                    zlib_include_path=zlib_builder.include_path,
                    zlib_lib_path=zlib_builder.lib_path,
                )
                with open('win32/config.mk', 'r+') as cf:
                    contents = cf.read()
                    cf.seek(0)
                    cf.write(vars)
                    cf.write(contents)
                f.write("nmake -f NMakefile\n")
                # libcurl loves its _a suffixes on static library names
                f.write("cp Release\\src\\libssh2.lib Release\\src\\libssh2_a.lib\n")

    @property
    def output_dir_path(self):
        return 'libssh2-%s-%s' % (self.libssh2_version, self.vc_tag)

    @property
    def dll_paths(self):
        raise NotImplemented

    @property
    def include_path(self):
        return os.path.join(archives_path, self.output_dir_path, 'include')

    @property
    def lib_path(self):
        return os.path.join(archives_path, self.output_dir_path,
            'Release', 'src')

class LibcurlBuilder(Builder):
    def __init__(self, **kwargs):
        super(LibcurlBuilder, self).__init__(**kwargs)
        self.libcurl_version = kwargs.pop('libcurl_version')
        self.use_zlib = kwargs.pop('use_zlib')
        if self.use_zlib:
            self.zlib_version = kwargs.pop('zlib_version')
        self.use_openssl = kwargs.pop('use_openssl')
        if self.use_openssl:
            self.openssl_version = kwargs.pop('openssl_version')
        self.use_cares = kwargs.pop('use_cares')
        if self.use_cares:
            self.cares_version = kwargs.pop('cares_version')
        self.use_libssh2 = kwargs.pop('use_libssh2')
        if self.use_libssh2:
            self.libssh2_version = kwargs.pop('libssh2_version')

    @property
    def state_tag(self):
        return 'curl-%s-%s' % (self.libcurl_version, self.vc_tag)

    def build(self):
        fetch('https://curl.haxx.se/download/curl-%s.tar.gz' % self.libcurl_version)
        untar('curl-%s' % self.libcurl_version)
        curl_dir = rename_for_vc('curl-%s' % self.libcurl_version, self.vc_tag)
        with in_dir(os.path.join(curl_dir, 'winbuild')):
            with self.execute_batch() as f:
                f.write("patch -p1 < %s\n" % os.path.join(dir_here, 'winbuild', 'libcurl-fix-zlib-references.patch'))
                if self.use_dlls:
                    dll_or_static = 'dll'
                else:
                    dll_or_static = 'static'
                extra_options = ' mode=%s' % dll_or_static
                if self.use_zlib:
                    zlib_builder = ZlibBuilder(bitness=self.bitness, vc_version=self.vc_version, zlib_version=self.zlib_version)
                    f.write("set include=%%include%%;%s\n" % zlib_builder.include_path)
                    f.write("set lib=%%lib%%;%s\n" % zlib_builder.lib_path)
                    extra_options += ' WITH_ZLIB=%s' % dll_or_static
                if self.use_openssl:
                    openssl_builder = OpensslBuilder(bitness=self.bitness, vc_version=self.vc_version, openssl_version=self.openssl_version)
                    f.write("set include=%%include%%;%s\n" % openssl_builder.include_path)
                    f.write("set lib=%%lib%%;%s\n" % openssl_builder.lib_path)
                    extra_options += ' WITH_SSL=%s' % dll_or_static
                if self.use_cares:
                    cares_builder = CaresBuilder(bitness=self.bitness, vc_version=self.vc_version, cares_version=self.cares_version)
                    f.write("set include=%%include%%;%s\n" % cares_builder.include_path)
                    f.write("set lib=%%lib%%;%s\n" % cares_builder.lib_path)
                    extra_options += ' WITH_CARES=%s' % dll_or_static
                if self.use_libssh2:
                    libssh2_builder = Libssh2Builder(bitness=self.bitness, vc_version=self.vc_version, libssh2_version=self.libssh2_version, zlib_version=self.zlib_version, openssl_version=self.openssl_version)
                    f.write("set include=%%include%%;%s\n" % libssh2_builder.include_path)
                    f.write("set lib=%%lib%%;%s\n" % libssh2_builder.lib_path)
                    extra_options += ' WITH_SSH2=%s' % dll_or_static
                if openssl_version_tuple >= (1, 1):
                    # openssl 1.1.0
                    # https://curl.haxx.se/mail/lib-2016-08/0104.html
                    # https://github.com/curl/curl/issues/984
                    # crypt32.lib: http://stackoverflow.com/questions/37522654/linking-with-openssl-lib-statically
                    extra_options += ' MAKE="NMAKE /e" SSL_LIBS="libssl.lib libcrypto.lib crypt32.lib"'
                f.write("nmake /f Makefile.vc ENABLE_IDN=no%s\n" % extra_options)

    @property
    def output_dir_name(self):
        if self.use_dlls:
            dll_or_static = 'dll'
        else:
            dll_or_static = 'static'
        if self.use_zlib:
            zlib_part = '-zlib-%s' % dll_or_static
        else:
            zlib_part = ''
        # don't know when spnego is on and when it is off yet
        if False:
            spnego_part = '-spnego'
        else:
            spnego_part = ''
        bitness_indicators = {32: 'x86', 64: 'x64'}
        bitness_indicator = bitness_indicators[self.bitness]
        if self.use_openssl:
            winssl_part = ''
            openssl_part = '-ssl-%s' % dll_or_static
        else:
            winssl_part = '-winssl'
            openssl_part = ''
        if self.use_cares:
            cares_part = '-cares-%s' % dll_or_static
        else:
            cares_part = ''
        if self.use_libssh2:
            libssh2_part = '-ssh2-%s' % dll_or_static
        else:
            libssh2_part = ''
        output_dir_name = 'libcurl-vc-%s-release-%s%s%s%s%s-ipv6-sspi%s%s' % (
            bitness_indicator, dll_or_static, openssl_part, cares_part, zlib_part, libssh2_part, spnego_part, winssl_part)
        return output_dir_name

    @property
    def output_dir_path(self):
        curl_dir = 'curl-%s-%s/builds/%s' % (
            self.libcurl_version, self.vc_tag, self.output_dir_name)
        return curl_dir

    @property
    def dll_paths(self):
        return [
            os.path.join(self.output_dir_path, 'bin', 'libcurl.dll'),
        ]

class PycurlBuilder(Builder):
    def __init__(self, **kwargs):
        self.python_release = kwargs.pop('python_release')
        kwargs['vc_version'] = python_vc_versions[self.python_release]
        super(PycurlBuilder, self).__init__(**kwargs)
        self.pycurl_version = kwargs.pop('pycurl_version')
        self.libcurl_version = kwargs.pop('libcurl_version')
        self.zlib_version = kwargs.pop('zlib_version')
        self.use_zlib = kwargs.pop('use_zlib')
        self.openssl_version = kwargs.pop('openssl_version')
        self.use_openssl = kwargs.pop('use_openssl')
        self.cares_version = kwargs.pop('cares_version')
        self.use_cares = kwargs.pop('use_cares')
        self.libssh2_version = kwargs.pop('libssh2_version')
        self.use_libssh2 = kwargs.pop('use_libssh2')

    @property
    def python_path(self):
        if build_wheels:
            python_path = os.path.join(archives_path, 'venv-%s-%s' % (self.python_release, self.bitness), 'scripts', 'python')
        else:
            python_path = PythonBinary(self.python_release, self.bitness).executable_path
        return python_path

    @property
    def platform_indicator(self):
        platform_indicators = {32: 'win32', 64: 'win-amd64'}
        return platform_indicators[self.bitness]

    def build(self, targets):
        libcurl_builder = LibcurlBuilder(bitness=self.bitness,
            vc_version=self.vc_version,
            use_zlib=self.use_zlib,
            zlib_version=self.zlib_version,
            use_openssl=self.use_openssl,
            openssl_version=self.openssl_version,
            use_cares=self.use_cares,
            cares_version=self.cares_version,
            use_libssh2=self.use_libssh2,
            libssh2_version=self.libssh2_version,
            libcurl_version=self.libcurl_version)
        libcurl_dir = os.path.abspath(libcurl_builder.output_dir_path)
        dll_paths = libcurl_builder.dll_paths
        if self.use_zlib:
            zlib_builder = ZlibBuilder(bitness=self.bitness,
                vc_version=self.vc_version,
                zlib_version=self.zlib_version,
            )
            dll_paths += zlib_builder.dll_paths
        dll_paths = [os.path.abspath(dll_path) for dll_path in dll_paths]
        with in_dir(os.path.join('pycurl-%s' % self.pycurl_version)):
            dest_lib_path = 'build/lib.%s-%s' % (self.platform_indicator,
                self.python_release)
            # exists for building additional targets for the same python version
            mkdir_p(dest_lib_path)
            if self.use_dlls:
                for dll_path in dll_paths:
                    shutil.copy(dll_path, dest_lib_path)
            with self.execute_batch() as f:
                f.write("%s setup.py docstrings\n" % (self.python_path,))
                if self.use_dlls:
                    libcurl_arg = '--use-libcurl-dll'
                else:
                    libcurl_arg = '--libcurl-lib-name=libcurl_a.lib'
                if self.use_openssl:
                    libcurl_arg += ' --with-openssl'
                    if openssl_version_tuple >= (1, 1):
                        libcurl_arg += ' --openssl-lib-name=""'
                    openssl_builder = OpensslBuilder(bitness=self.bitness, vc_version=self.vc_version, openssl_version=self.openssl_version)
                    f.write("set include=%%include%%;%s\n" % openssl_builder.include_path)
                    f.write("set lib=%%lib%%;%s\n" % openssl_builder.lib_path)
                #if build_wheels:
                    #f.write("call %s\n" % os.path.join('..', 'venv-%s-%s' % (self.python_release, self.bitness), 'Scripts', 'activate'))
                if build_wheels:
                    targets = targets + ['bdist_wheel']
                f.write("%s setup.py %s --curl-dir=%s %s\n" % (
                    self.python_path, ' '.join(targets), libcurl_dir, libcurl_arg))
            if 'bdist' in targets:
                zip_basename_orig = 'pycurl-%s.%s.zip' % (
                    self.pycurl_version, self.platform_indicator)
                zip_basename_new = 'pycurl-%s.%s-py%s.zip' % (
                    self.pycurl_version, self.platform_indicator, self.python_release)
                with zipfile.ZipFile('dist/%s' % zip_basename_orig, 'r') as src_zip:
                    with zipfile.ZipFile('dist/%s' % zip_basename_new, 'w') as dest_zip:
                        for name in src_zip.namelist():
                            parts = name.split('/')
                            while True:
                                popped = parts.pop(0)
                                if popped == 'python%s' % self.python_release.dotless or popped.startswith('venv-'):
                                    break
                            assert len(parts) > 0
                            new_name = '/'.join(parts)
                            print('Recompressing %s -> %s' % (name, new_name))

                            member = src_zip.open(name)
                            dest_zip.writestr(new_name, member.read(), zipfile.ZIP_DEFLATED)

def build_dependencies(bitnesses=(32, 64)):
    if use_libssh2:
        if not use_zlib:
            # technically we can build libssh2 without zlib but I don't want to bother
            raise ValueError('use_zlib must be True if use_libssh2 is True')
        if not use_openssl:
            raise ValueError('use_openssl must be True if use_libssh2 is True')

    if git_bin_path:
        os.environ['PATH'] += ";%s" % git_bin_path
    mkdir_p(archives_path)
    with in_dir(archives_path):
        for bitness in bitnesses:
            for vc_version in needed_vc_versions(python_versions):
                if opts.verbose:
                    print('Builddep for %s, %s-bit' % (vc_version, bitness))
                if use_zlib:
                    zlib_builder = ZlibBuilder(bitness=bitness, vc_version=vc_version, zlib_version=zlib_version)
                    step(zlib_builder.build, (), zlib_builder.state_tag)
                if use_openssl:
                    openssl_builder = OpensslBuilder(bitness=bitness, vc_version=vc_version, openssl_version=openssl_version)
                    step(openssl_builder.build, (), openssl_builder.state_tag)
                if use_cares:
                    cares_builder = CaresBuilder(bitness=bitness, vc_version=vc_version, cares_version=cares_version)
                    step(cares_builder.build, (), cares_builder.state_tag)
                if use_libssh2:
                    libssh2_builder = Libssh2Builder(bitness=bitness, vc_version=vc_version, libssh2_version=libssh2_version, zlib_version=zlib_version, openssl_version=openssl_version)
                    step(libssh2_builder.build, (), libssh2_builder.state_tag)
                libcurl_builder = LibcurlBuilder(bitness=bitness, vc_version=vc_version,
                    use_zlib=use_zlib, zlib_version=zlib_version,
                    use_openssl=use_openssl, openssl_version=openssl_version,
                    use_cares=use_cares, cares_version=cares_version,
                    use_libssh2=use_libssh2, libssh2_version=libssh2_version,
                    libcurl_version=libcurl_version)
                step(libcurl_builder.build, (), libcurl_builder.state_tag)

bitnesses = (32, 64)

def build():
    # note: adds git_bin_path to PATH if necessary, and creates archives_path
    build_dependencies(bitnesses)
    with in_dir(archives_path):
        def prepare_pycurl():
            #fetch('https://dl.bintray.com/pycurl/pycurl/pycurl-%s.tar.gz' % pycurl_version)
            if os.path.exists('pycurl-%s' % pycurl_version):
                #shutil.rmtree('pycurl-%s' % pycurl_version)
                subprocess.check_call([rm_path, '-rf', 'pycurl-%s' % pycurl_version])
            #subprocess.check_call([tar_path, 'xf', 'pycurl-%s.tar.gz' % pycurl_version])
            shutil.copytree('c:/dev/pycurl', 'pycurl-%s' % pycurl_version)
            if build_wheels:
                with in_dir('pycurl-%s' % pycurl_version):
                    subprocess.check_call(['sed', '-i',
                        's/from distutils.core import setup/from setuptools import setup/',
                        'setup.py'])

        prepare_pycurl()

        for bitness in bitnesses:
            for python_release in python_releases():
                targets = ['bdist', 'bdist_wininst', 'bdist_msi']
                vc_version = python_vc_versions[python_release]
                builder = PycurlBuilder(bitness=bitness, vc_version=vc_version,
                    python_release=python_release, pycurl_version=pycurl_version,
                    use_zlib=use_zlib, zlib_version=zlib_version,
                    use_openssl=use_openssl, openssl_version=openssl_version,
                    use_cares=use_cares, cares_version=cares_version,
                    use_libssh2=use_libssh2, libssh2_version=libssh2_version,
                    libcurl_version=libcurl_version)
                builder.build(targets)

def download_pythons():
    mkdir_p(archives_path)
    for version in python_versions:
        parts = [int(part) for part in version.split('.')]
        if parts[0] >= 3 and parts[1] >= 5:
            ext = 'exe'
            amd64_suffix = '-amd64'
        else:
            ext = 'msi'
            amd64_suffix = '.amd64'
        url = 'https://www.python.org/ftp/python/%s/python-%s.%s' % (version, version, ext)
        fetch(url, os.path.join(archives_path, 'python-%s.%s') % (version, ext))
        url = 'https://www.python.org/ftp/python/%s/python-%s%s.%s' % (version, version, amd64_suffix, ext)
        fetch(url, os.path.join(archives_path, 'python-%s%s.%s') % (version, amd64_suffix, ext))

def download_bootstrap_python():
    version = python_versions[-2]
    url = 'https://www.python.org/ftp/python/%s/python-%s.msi' % (version, version)
    fetch(url)

def install_virtualenv():
    with in_dir(archives_path):
        fetch('https://pypi.python.org/packages/source/v/virtualenv/virtualenv-%s.tar.gz' % virtualenv_version)
        for bitness in bitnesses:
            for python_release in python_releases():
                print('Installing virtualenv %s for Python %s (%s bit)' % (virtualenv_version, python_release, bitness))
                sys.stdout.flush()
                untar('virtualenv-%s' % virtualenv_version)
                with in_dir('virtualenv-%s' % virtualenv_version):
                    python_binary = PythonBinary(python_release, bitness)
                    cmd = [python_binary.executable_path, 'setup.py', 'install']
                    subprocess.check_call(cmd)

def create_virtualenvs():
    for bitness in bitnesses:
        for python_release in python_releases():
            print('Creating a virtualenv for Python %s (%s bit)' % (python_release, bitness))
            sys.stdout.flush()
            with in_dir(archives_path):
                python_binary = PythonBinary(python_release, bitness)
                venv_basename = 'venv-%s-%s' % (python_release, bitness)
                cmd = [python_binary.executable_path, '-m', 'virtualenv', venv_basename]
                subprocess.check_call(cmd)

import optparse

parser = optparse.OptionParser()
parser.add_option('-b', '--bitness', help='Bitnesses build for, comma separated')
parser.add_option('-p', '--python', help='Python versions to build for, comma separated')
parser.add_option('-v', '--verbose', help='Print what is being done', action='store_true')
opts, args = parser.parse_args()

if opts.bitness:
    chosen_bitnesses = [int(bitness) for bitness in opts.bitness.split(',')]
    for bitness in chosen_bitnesses:
        if bitness not in bitnesses:
            print('Invalid bitness %d' % bitness)
            exit(2)
    bitnesses = chosen_bitnesses

if opts.python:
    chosen_pythons = opts.python.split(',')
    chosen_python_versions = []
    for python in chosen_pythons:
        python = python.replace('.', '')
        python = python[0] + '.' + python[1] + '.'
        ok = False
        for python_version in python_versions:
            if python_version.startswith(python):
                chosen_python_versions.append(python_version)
                ok = True
        if not ok:
            print('Invalid python %s' % python)
            exit(2)
    python_versions = chosen_python_versions

# https://stackoverflow.com/questions/35569042/python-3-ssl-certificate-verify-failed
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

if len(args) > 0:
    if args[0] == 'download':
        download_pythons()
    elif args[0] == 'bootstrap':
        download_bootstrap_python()
    elif args[0] == 'builddeps':
        build_dependencies(bitnesses)
    elif args[0] == 'installvirtualenv':
        install_virtualenv()
    elif args[0] == 'createvirtualenvs':
        create_virtualenvs()
    else:
        print('Unknown command: %s' % args[0])
        exit(2)
else:
    build()
