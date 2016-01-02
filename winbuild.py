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

# work directory for downloading dependencies and building everything
root = 'c:/dev/build-pycurl'
# where msysgit is installed
git_root = 'c:/program files/git'
# which versions of python to build against
python_versions = ['2.6.6', '2.7.10', '3.2.5', '3.3.5', '3.4.3', '3.5.0']
# where pythons are installed
python_path_template = 'c:/dev/%(bitness)s/python%(python_version)s/python'
vc_paths = {
    # where msvc 9 is installed, for python 2.6 through 3.2
    'vc9': None,
    # where msvc 10 is installed, for python 3.3 through 3.4
    'vc10': None,
    # where msvc 14 is installed, for python 3.5
    'vc14': None,
}
# whether to link libcurl against zlib
use_zlib = True
# which version of zlib to use, will be downloaded from internet
zlib_version = '1.2.8'
# whether to use openssl instead of winssl
use_openssl = True
# which version of openssl to use, will be downloaded from internet
openssl_version = '1.0.2e'
# which version of libcurl to use, will be downloaded from the internet
libcurl_version = '7.46.0'
# pycurl version to build, we should know this ourselves
pycurl_version = '7.19.5.3'

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
nasm_path = 'c:/program files (x86)/nasm'

import os, os.path, sys, subprocess, shutil, contextlib, zipfile

archives_path = os.path.join(root, 'archives')
state_path = os.path.join(root, 'state')
#git_bin_path = os.path.join(git_root, 'bin')
git_bin_path = ''
git_path = os.path.join(git_bin_path, 'git')
rm_path = os.path.join(git_bin_path, 'rm')
tar_path = os.path.join(git_bin_path, 'tar')
python_vc_versions = {
    '2.6': 'vc9',
    '2.7': 'vc9',
    '3.2': 'vc9',
    '3.3': 'vc10',
    '3.4': 'vc10',
    '3.5': 'vc14',
}
vc_versions = vc_paths.keys()
dir_here = os.path.abspath(os.path.dirname(__file__))

try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen

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
    if not os.path.exists(state_path):
        os.makedirs(state_path)
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
                f.write("patch -p0 < %s\n" % os.path.join(dir_here, 'winbuild', 'fix-openssl-crt.patch'))
                f.write("perl Configure VC-WIN32 --prefix=%s\\build\n" % openssl_dir)
                f.write("call ms\\do_nasm\n")
                f.write("nmake -f ms\\nt.mak\n")

    @property
    def output_dir_path(self):
        return 'openssl-%s-%s/build' % (self.openssl_version, self.vc_tag)

    @property
    def dll_paths(self):
        raise NotImplemented

class LibcurlBuilder(Builder):
    def __init__(self, **kwargs):
        super(LibcurlBuilder, self).__init__(**kwargs)
        self.libcurl_version = kwargs.pop('libcurl_version')
        self.use_zlib = kwargs.pop('use_zlib')
        if self.use_zlib:
            self.zlib_version = kwargs.pop('zlib_version')

    @property
    def state_tag(self):
        return 'curl-%s-%s' % (self.libcurl_version, self.vc_tag)

    def build(self):
        fetch('http://curl.haxx.se/download/curl-%s.tar.gz' % self.libcurl_version)
        untar('curl-%s' % self.libcurl_version)
        curl_dir = rename_for_vc('curl-%s' % self.libcurl_version, self.vc_tag)
        with in_dir(os.path.join(curl_dir, 'winbuild')):
            with self.execute_batch() as f:
                f.write("patch -p1 < %s\n" % os.path.join(dir_here, 'winbuild', 'fix-zlib-references.patch'))
                if self.use_zlib:
                    f.write("set include=%%include%%;%s\n" % os.path.join(archives_path, 'zlib-%s-%s' % (self.zlib_version, self.vc_tag)))
                    f.write("set lib=%%lib%%;%s\n" % os.path.join(archives_path, 'zlib-%s-%s' % (self.zlib_version, self.vc_tag)))
                    if self.use_dlls:
                        extra_options = ' WITH_ZLIB=dll'
                    else:
                        extra_options = ' WITH_ZLIB=static'
                else:
                    extra_options = ''
                if self.use_dlls:
                    extra_options += ' mode=dll'
                else:
                    extra_options += ' mode=static'
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
        output_dir_name = 'libcurl-vc-%s-release-%s%s-ipv6-sspi%s-winssl' % (
            bitness_indicator, dll_or_static, zlib_part, spnego_part)
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
        self.python_version = kwargs.pop('python_version')
        kwargs['vc_version'] = python_vc_versions[self.python_version]
        super(PycurlBuilder, self).__init__(**kwargs)
        self.pycurl_version = kwargs.pop('pycurl_version')
        self.libcurl_version = kwargs.pop('libcurl_version')
        self.zlib_version = kwargs.pop('zlib_version')
        self.use_zlib = kwargs.pop('use_zlib')

    @property
    def python_path(self):
        return python_path_template % dict(
            python_version=self.python_version.replace('.', ''),
            bitness=self.bitness)

    @property
    def platform_indicator(self):
        platform_indicators = {32: 'win32', 64: 'win-amd64'}
        return platform_indicators[self.bitness]

    def build(self, targets):
        libcurl_builder = LibcurlBuilder(bitness=self.bitness,
            vc_version=self.vc_version,
            use_zlib=self.use_zlib,
            zlib_version=self.zlib_version,
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
                self.python_version)
            if not os.path.exists(dest_lib_path):
                # exists for building additional targets for the same python version
                os.makedirs(dest_lib_path)
            if self.use_dlls:
                for dll_path in dll_paths:
                    shutil.copy(dll_path, dest_lib_path)
            with self.execute_batch() as f:
                f.write("%s setup.py docstrings\n" % (self.python_path,))
                if self.use_dlls:
                    libcurl_arg = '--use-libcurl-dll'
                else:
                    libcurl_arg = '--libcurl-lib-name=libcurl_a.lib'
                f.write("%s setup.py %s --curl-dir=%s %s\n" % (
                    self.python_path, ' '.join(targets), libcurl_dir, libcurl_arg))
            if 'bdist' in targets:
                zip_basename_orig = 'pycurl-%s.%s.zip' % (
                    self.pycurl_version, self.platform_indicator)
                zip_basename_new = 'pycurl-%s.%s-py%s.zip' % (
                    self.pycurl_version, self.platform_indicator, self.python_version)
                with zipfile.ZipFile('dist/%s' % zip_basename_orig, 'r') as src_zip:
                    with zipfile.ZipFile('dist/%s' % zip_basename_new, 'w') as dest_zip:
                        for name in src_zip.namelist():
                            parts = name.split('/')
                            while parts[0] != 'python%s' % self.python_version.replace('.', ''):
                                parts.pop(0)
                            assert len(parts) > 0
                            new_name = '/'.join(parts)
                            print('Recompressing %s -> %s' % (name, new_name))

                            member = src_zip.open(name)
                            dest_zip.writestr(new_name, member.read(), zipfile.ZIP_DEFLATED)

def build_dependencies():
    if git_bin_path:
        os.environ['PATH'] += ";%s" % git_bin_path
    if not os.path.exists(archives_path):
        os.makedirs(archives_path)
    with in_dir(archives_path):
        for bitness in (32, 64):
            for vc_version in vc_versions:
                if use_zlib:
                    zlib_builder = ZlibBuilder(bitness=bitness, vc_version=vc_version, zlib_version=zlib_version)
                    step(zlib_builder.build, (), zlib_builder.state_tag)
                if use_openssl:
                    openssl_builder = OpensslBuilder(bitness=bitness, vc_version=vc_version, openssl_version=openssl_version)
                    step(openssl_builder.build, (), openssl_builder.state_tag)
                libcurl_builder = LibcurlBuilder(bitness=bitness, vc_version=vc_version,
                    use_zlib=use_zlib, zlib_version=zlib_version, libcurl_version=libcurl_version)
                step(libcurl_builder.build, (), libcurl_builder.state_tag)

def build():
    # note: adds git_bin_path to PATH if necessary, and creates archives_path
    build_dependencies()
    with in_dir(archives_path):
        def prepare_pycurl():
            #fetch('http://pycurl.sourceforge.net/download/pycurl-%s.tar.gz' % pycurl_version)
            if os.path.exists('pycurl-%s' % pycurl_version):
                #shutil.rmtree('pycurl-%s' % pycurl_version)
                subprocess.check_call([rm_path, '-rf', 'pycurl-%s' % pycurl_version])
            #subprocess.check_call([tar_path, 'xf', 'pycurl-%s.tar.gz' % pycurl_version])
            shutil.copytree('c:/dev/pycurl', 'pycurl-%s' % pycurl_version)

        prepare_pycurl()

        for bitness in (32, 64):
            python_releases = ['.'.join(version.split('.')[:2]) for version in python_versions]
            for python_version in python_releases:
                targets = ['bdist', 'bdist_wininst', 'bdist_msi']
                vc_version = python_vc_versions[python_version]
                builder = PycurlBuilder(bitness=bitness, vc_version=vc_version,
                    python_version=python_version, pycurl_version=pycurl_version,
                    use_zlib=use_zlib, zlib_version=zlib_version, libcurl_version=libcurl_version)
                builder.build(targets)

def download_pythons():
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

if len(sys.argv) > 1:
    if sys.argv[1] == 'download':
        download_pythons()
    elif sys.argv[1] == 'bootstrap':
        download_bootstrap_python()
    elif sys.argv[1] == 'builddeps':
        build_dependencies()
    else:
        print('Unknown command: %s' % sys.argv[1])
        exit(2)
else:
    build()
