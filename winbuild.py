# This file builds official Windows binaries of PycURL and all of its dependencies.
#
# It is written to be run on a system dedicated to building pycurl, but can be configured
# for any system that has the required tools installed.
#
# Generally, the workflow of building pycurl binaries is as follows:
#  1. Install git for windows. Use it to check out pycurl repository on the build system.
#  2. There must be a python installation already present on the build system
#     in order to execute this file at all. It doesn't matter what the python
#     version of the bootstrap python is. The first step is to install some
#     version of python. It saves effort to install one of the versions that will be used
#     to build pycurl later, however if this is done the target path should be
#     in line with where all other pythons are going to be installed (i.e. c:/dev/{32,64}/pythonXY by default).
#     Try these binaries:
#     https://www.python.org/ftp/python/3.8.0/python-3.8.0.exe
#     https://www.python.org/ftp/python/3.8.0/python-3.8.0-amd64.exe
#     Then execute:
#     c:\dev\python-3.8.0.exe /norestart /passive InstallAllUsers=1 Include_test=0 Include_doc=0 Include_launcher=0 Include_tcltk=0 TargetDir=c:\dev\32\python38
#  3. Define python versions to build for in the configuration below, then
#     run `python winbuild.py download` and `python winbuild.py installpy` to install them.
#  4. Download and install visual studio. Any edition of 2015 or newer should work;
#     2019 in particular (including community edition) provides batch files to set up a 2015 build environment,
#     such that there is no reason to get an older version.
#  5. You may need to install platform sdk/windows sdk, especially if you installed community edition of
#     visual studio as opposed to a fuller edition. Try https://developer.microsoft.com/en-us/windows/downloads/windows-10-sdk.
#  6. You may also need to install windows 8.1 sdk for building nghttp2 with cmake.
#     See https://developer.microsoft.com/en-us/windows/downloads/sdk-archive.
#  7. Download and install perl. This script is tested with activestate perl, although
#     other distributions may also work. activestate perl can be downloaded at http://www.activestate.com/activeperl/downloads,
#     although it now requires registration to download thus using a third party download site may be preferable.
#  8. Download and install nasm: https://www.nasm.us/pub/nasm/releasebuilds/?C=M;O=D
#     (homepage: http://www.nasm.us/)
# 9a. Not needed since nghttp2 is currently built using gmake: download and install cmake: https://cmake.org/download/
# 9b. Download and install gmake: http://gnuwin32.sourceforge.net/packages/make.htm
# 10. Run `python winbuild.py builddeps` to compile all dependencies for all environments (32/64 bit and python versions).
# 11. Optional: run `python winbuild.py assembledeps` to assemble all dependencies into archives suitable for use in appveyor.
# 12. Run `python winbuild.py installvirtualenv` to install virtualenv in all python interpreters.
# 13. Run `python winbuild.py createvirtualenvs` to create virtualenvs used for pycurl compilation.
# 14. Run `python winbuild.py` to compile pycurl in all defined configurations.
# 15. Optional: run `python winbuild.py assemble` to assemble all built versions of pycurl in the current directory.

class Config:
    '''User-adjustable configuration.
    
    This class contains version numbers for dependencies,
    which dependencies to use,
    and where various binaries, headers and libraries are located in the filesystem.
    '''
    
    # work directory for downloading dependencies and building everything
    root = 'c:/dev/build-pycurl'
    # where msysgit is installed
    git_root = 'c:/program files/git'
    msysgit_bin_paths = [
        "c:\\Program Files\\Git\\bin",
        "c:\\Program Files\\Git\\usr\\bin",
        #"c:\\Program Files\\Git\\mingw64\\bin",
    ]
    # where NASM is installed, for building OpenSSL
    nasm_path = ('c:/dev/nasm', 'c:/program files/nasm', 'c:/program files (x86)/nasm')
    cmake_path = r"c:\Program Files\CMake\bin\cmake.exe"
    gmake_path = r"c:\Program Files (x86)\GnuWin32\bin\make.exe"
    # where ActiveState Perl is installed, for building 64-bit OpenSSL
    activestate_perl_path = ('c:/perl64', r'c:\dev\perl64')
    # which versions of python to build against
    #python_versions = ['2.7.10', '3.2.5', '3.3.5', '3.4.3', '3.5.4', '3.6.2']
    # these require only vc9 and vc14
    python_versions = ['3.5.4', '3.6.8', '3.7.6', '3.8.1']
    # where pythons are installed
    python_path_template = 'c:/dev/%(bitness)s/python%(python_release)s/python'
    # overrides only, defaults are given in default_vc_paths below
    vc_paths = {
        # where msvc 9/vs 2008 is installed, for python 2.6 through 3.2
        'vc9': None,
        # where msvc 10/vs 2010 is installed, for python 3.3 through 3.4
        'vc10': None,
        # where msvc 14/vs 2015 is installed, for python 3.5 through 3.8
        'vc14': None,
    }
    # whether to link libcurl against zlib
    use_zlib = True
    # which version of zlib to use, will be downloaded from internet
    zlib_version = '1.2.11'
    # whether to use openssl instead of winssl
    use_openssl = True
    # which version of openssl to use, will be downloaded from internet
    openssl_version = '1.1.1d'
    # whether to use c-ares
    use_cares = True
    cares_version = '1.15.0'
    # whether to use libssh2
    use_libssh2 = True
    libssh2_version = '1.9.0'
    use_nghttp2 = True
    nghttp2_version = '1.40.0'
    use_libidn = False
    libiconv_version = '1.16'
    libidn_version = '1.35'
    # which version of libcurl to use, will be downloaded from internet
    libcurl_version = '7.68.0'
    # virtualenv version
    virtualenv_version = '15.1.0'
    # whether to build binary wheels
    build_wheels = True
    # pycurl version to build, we should know this ourselves
    pycurl_version = '7.44.0'

    # Sometimes vc14 does not include windows sdk path in vcvars which breaks stuff.
    # another application for this is to supply normaliz.lib for vc9
    # which has an older version that doesn't have the symbols we need
    windows_sdk_path = 'c:\\program files (x86)\\microsoft sdks\\windows\\v7.1a'
    
    # See the note below about VCTargetsPath and
    # https://stackoverflow.com/questions/16092169/why-does-msbuild-look-in-c-for-microsoft-cpp-default-props-instead-of-c-progr.
    # Since we are targeting vc14, use the v140 path.
    vc_targets_path = "c:\\Program Files (x86)\\MSBuild\\Microsoft.Cpp\\v4.0\\v140"
    #vc_targets_path = "c:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\Community\\MSBuild\\Current"
    
    # Where the msbuild that is part of visual studio lives
    msbuild_bin_path = "c:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\Community\\MSBuild\\Current\\Bin"

# ***
# No user-serviceable parts beyond this point.
# ***

# OpenSSL build resources including 64-bit builds:
# http://stackoverflow.com/questions/158232/how-do-you-compile-openssl-for-x64
# https://wiki.openssl.org/index.php/Compilation_and_Installation
# http://developer.covenanteyes.com/building-openssl-for-visual-studio/

import os, os.path, sys, subprocess, shutil, contextlib, zipfile, re
from winbuild.utils import *
from winbuild.config import *
from winbuild.builder import *
from winbuild.nghttp_gmake import *
from winbuild.tools import *
from winbuild.zlib import *
from winbuild.openssl import *
from winbuild.cares import *
from winbuild.ssh import *
from winbuild.curl import *
from winbuild.pycurl import *

user_config = {}
for attr in dir(Config):
    if attr.startswith('_'):
        continue
    user_config[attr] = getattr(Config, attr)

# This must be at top level as __file__ can be a relative path
# and changing current directory will break it
DIR_HERE = os.path.abspath(os.path.dirname(__file__))

def fetch_to_archives(url):
    mkdir_p(config.archives_path)
    path = os.path.join(config.archives_path, os.path.basename(url))
    fetch(url, path)

@contextlib.contextmanager
def step(step_fn, args, target_dir):
    #step = step_fn.__name__
    state_tag = target_dir
    mkdir_p(config.state_path)
    state_file_path = os.path.join(config.state_path, state_tag)
    if not os.path.exists(state_file_path) or not os.path.exists(target_dir):
        step_fn(*args)
    with open(state_file_path, 'w'):
        pass

def dep_builders(bconf):
    builders = []
    if config.use_zlib:
        builders.append(ZlibBuilder)
    if config.use_openssl:
        builders.append(OpensslBuilder)
    if config.use_cares:
        builders.append(CaresBuilder)
    if config.use_libssh2:
        builders.append(Libssh2Builder)
    if config.use_nghttp2:
        builders.append(Nghttp2Builder)
    if config.use_libidn:
        builders.append(LibiconvBuilder)
        builders.append(LibidnBuilder)
    builders.append(LibcurlBuilder)
    builders = [
        cls(bconf=bconf)
        for cls in builders
    ]
    return builders

def build_dependencies(config):
    if config.use_libssh2:
        if not config.use_zlib:
            # technically we can build libssh2 without zlib but I don't want to bother
            raise ValueError('use_zlib must be true if use_libssh2 is true')
        if not config.use_openssl:
            raise ValueError('use_openssl must be true if use_libssh2 is true')

    if config.git_bin_path:
        os.environ['PATH'] += ";%s" % config.git_bin_path
    mkdir_p(config.archives_path)
    with in_dir(config.archives_path):
        for bconf in buildconfigs():
                if opts.verbose:
                    print('Builddep for %s, %s-bit' % (bconf.vc_version, bconf.bitness))
                for builder in dep_builders(bconf):
                    step(builder.build, (), builder.state_tag)

def build(config):
    # note: adds git_bin_path to PATH if necessary, and creates archives_path
    build_dependencies(config)
    with in_dir(config.archives_path):
        for bitness in config.bitnesses:
            for python_release in config.python_releases:
                targets = ['bdist', 'bdist_wininst', 'bdist_msi']
                vc_version = PYTHON_VC_VERSIONS[python_release]
                bconf = BuildConfig(config, bitness=bitness, vc_version=vc_version)
                builder = PycurlBuilder(bconf=bconf, python_release=python_release)
                builder.prepare_tree()
                builder.build(targets)

def assemble(config):
    rm_rf(config, 'dist')
    mkdir_p('dist')
    for bitness in config.bitnesses:
        for python_release in config.python_releases:
            vc_version = PYTHON_VC_VERSIONS[python_release]
            bconf = BuildConfig(config, bitness=bitness, vc_version=vc_version)
            builder = PycurlBuilder(bconf=bconf, python_release=python_release)
            print(builder.build_dir_name)
            sys.stdout.flush()
            src = os.path.join(config.archives_path, builder.build_dir_name, 'dist')
            cp_r(config, src, '.')

def python_metas():
    metas = []
    for version in config.python_versions:
        parts = [int(part) for part in version.split('.')]
        if parts[0] >= 3 and parts[1] >= 5:
            ext = 'exe'
            amd64_suffix = '-amd64'
        else:
            ext = 'msi'
            amd64_suffix = '.amd64'
        url_32 = 'https://www.python.org/ftp/python/%s/python-%s.%s' % (version, version, ext)
        url_64 = 'https://www.python.org/ftp/python/%s/python-%s%s.%s' % (version, version, amd64_suffix, ext)
        meta = dict(
            version=version, ext=ext, amd64_suffix=amd64_suffix,
            url_32=url_32, url_64=url_64,
            installed_path_32 = 'c:\\dev\\32\\python%d%d' % (parts[0], parts[1]),
            installed_path_64 = 'c:\\dev\\64\\python%d%d' % (parts[0], parts[1]),
        )
        metas.append(meta)
    return metas

def download_pythons(config):
    for meta in python_metas():
        for bitness in config.bitnesses:
            fetch_to_archives(meta['url_%d' % bitness])

def install_pythons(config):
    for meta in python_metas():
        for bitness in config.bitnesses:
            if not os.path.exists(meta['installed_path_%d' % bitness]):
                install_python(config, meta, bitness)

# http://eddiejackson.net/wp/?p=10276
def install_python(config, meta, bitness):
    archive_path = fix_slashes(os.path.join(config.archives_path, os.path.basename(meta['url_%d' % bitness])))
    if meta['ext'] == 'exe':
        cmd = [archive_path]
    else:
        cmd = ['msiexec', '/i', archive_path, '/norestart']
    cmd += ['/passive', 'InstallAllUsers=1',
            'Include_test=0', 'Include_doc=0', 'Include_launcher=0',
            'Include_tcltk=0',
            'TargetDir=%s' % meta['installed_path_%d' % bitness],
        ]
    sys.stdout.write('Installing python %s (%d bit)\n' % (meta['version'], bitness))
    print(' '.join(cmd))
    sys.stdout.flush()
    check_call(cmd)

def download_bootstrap_python(config):
    version = config.python_versions[-2]
    url = 'https://www.python.org/ftp/python/%s/python-%s.msi' % (version, version)
    fetch(url)

def install_virtualenv(config):
    with in_dir(config.archives_path):
        #fetch('https://pypi.python.org/packages/source/v/virtualenv/virtualenv-%s.tar.gz' % virtualenv_version)
        fetch('https://pypi.python.org/packages/d4/0c/9840c08189e030873387a73b90ada981885010dd9aea134d6de30cd24cb8/virtualenv-15.1.0.tar.gz')
        for bitness in config.bitnesses:
            for python_release in config.python_releases:
                print('Installing virtualenv %s for Python %s (%s bit)' % (config.virtualenv_version, python_release, bitness))
                sys.stdout.flush()
                untar(config, 'virtualenv-%s' % config.virtualenv_version)
                with in_dir('virtualenv-%s' % config.virtualenv_version):
                    python_binary = PythonBinary(python_release, bitness)
                    cmd = [python_binary.executable_path(config), 'setup.py', 'install']
                    check_call(cmd)

def create_virtualenvs(config):
    for bitness in config.bitnesses:
        for python_release in config.python_releases:
            print('Creating a virtualenv for Python %s (%s bit)' % (python_release, bitness))
            sys.stdout.flush()
            with in_dir(config.archives_path):
                python_binary = PythonBinary(python_release, bitness)
                venv_basename = 'venv-%s-%s' % (python_release, bitness)
                cmd = [python_binary.executable_path(config), '-m', 'virtualenv', venv_basename]
                check_call(cmd)

def assemble_deps(config):
    rm_rf(config, 'deps')
    os.mkdir('deps')
    for bconf in buildconfigs():
        print(bconf.vc_tag)
        sys.stdout.flush()
        dest = os.path.join('deps', bconf.vc_tag)
        os.mkdir(dest)
        for builder in dep_builders(bconf):
            cp_r(config, builder.include_path, dest)
            cp_r(config, builder.lib_path, dest)
            with zipfile.ZipFile(os.path.join('deps', bconf.vc_tag + '.zip'), 'w', zipfile.ZIP_DEFLATED) as zip:
                for root, dirs, files in os.walk(dest):
                    for file in files:
                        path = os.path.join(root, file)
                        zip_name = path[len(dest)+1:]
                        zip.write(path, zip_name)

def get_deps():
    import struct
    
    python_release = sys.version_info[:2]
    vc_version = PYTHON_VC_VERSIONS['.'.join(map(str, python_release))]
    bitness = struct.calcsize('P') * 8
    vc_tag = '%s-%d' % (vc_version, bitness)
    fetch('https://dl.bintray.com/pycurl/deps/%s.zip' % vc_tag)
    check_call(['unzip', '-d', 'deps', vc_tag + '.zip'])

import optparse

parser = optparse.OptionParser()
parser.add_option('-b', '--bitness', help='Bitnesses build for, comma separated')
parser.add_option('-p', '--python', help='Python versions to build for, comma separated')
parser.add_option('-v', '--verbose', help='Print what is being done', action='store_true')
opts, args = parser.parse_args()

if opts.bitness:
    chosen_bitnesses = [int(bitness) for bitness in opts.bitness.split(',')]
    for bitness in chosen_bitnesses:
        if bitness not in BITNESSES:
            print('Invalid bitness %d' % bitness)
            exit(2)
else:
    chosen_bitnesses = BITNESSES

if opts.python:
    chosen_pythons = opts.python.split(',')
    chosen_python_versions = []
    for python in chosen_pythons:
        python = python.replace('.', '')
        python = python[0] + '.' + python[1] + '.'
        ok = False
        for python_version in Config.python_versions:
            if python_version.startswith(python):
                chosen_python_versions.append(python_version)
                ok = True
        if not ok:
            print('Invalid python %s' % python)
            exit(2)
else:
    chosen_python_versions = Config.python_versions

config = ExtendedConfig(user_config,
    bitnesses=chosen_bitnesses,
    python_versions=chosen_python_versions,
    winbuild_root=DIR_HERE,
)

def buildconfigs():
    return [BuildConfig(config, bitness=bitness, vc_version=vc_version)
        for bitness in config.bitnesses
        for vc_version in needed_vc_versions(config, config.python_versions)
    ]

if len(args) > 0:
    if args[0] == 'download':
        download_pythons(config)
    elif args[0] == 'bootstrap':
        download_bootstrap_python(config)
    elif args[0] == 'installpy':
        install_pythons(config)
    elif args[0] == 'builddeps':
        build_dependencies(config)
    elif args[0] == 'installvirtualenv':
        install_virtualenv(config)
    elif args[0] == 'createvirtualenvs':
        create_virtualenvs(config)
    elif args[0] == 'assembledeps':
        assemble_deps(config)
    elif args[0] == 'assemble':
        assemble(config)
    elif args[0] == 'getdeps':
        get_deps()
    else:
        print('Unknown command: %s' % args[0])
        exit(2)
else:
    build(config)
