# Bootstrap python binary:
# http://www.python.org/ftp/python/3.3.4/python-3.3.4.msi
# http://www.python.org/ftp/python/3.3.4/python-3.3.4.amd64.msi
# msvc9/vs2008 express:
# http://go.microsoft.com/?linkid=7729279
# msvc10/vs2010 express:
# http://go.microsoft.com/?linkid=9709949

# work directory for downloading dependencies and building everything
root = 'c:/dev/build-pycurl'
# where msysgit is installed
git_root = 'c:/program files/git'
# which versions of python to build against
python_versions = ['2.6.6', '2.7.6', '3.2.5', '3.3.5', '3.4.1']
# where pythons are installed
python_path_template = 'c:/python%s/python'
vc_paths = {
    # where msvc 9 is installed, for python 2.6 through 3.2
    'vc9': 'c:/program files/microsoft visual studio 9.0',
    # where msvc 10 is installed, for python 3.3
    'vc10': 'c:/program files/microsoft visual studio 10.0',
}
# whether to link libcurl against zlib
use_zlib = True
# which version of zlib to use, will be downloaded from internet
zlib_version = '1.2.8'
# which version of libcurl to use, will be downloaded from the internet
libcurl_version = '7.37.0'
# pycurl version to build, we should know this ourselves
pycurl_version = '7.19.5.1'

import os, os.path, sys, subprocess, shutil, contextlib

archives_path = os.path.join(root, 'archives')
state_path = os.path.join(root, 'state')
git_bin_path = os.path.join(git_root, 'bin')
git_path = os.path.join(git_bin_path, 'git')
rm_path = os.path.join(git_bin_path, 'rm')
tar_path = os.path.join(git_bin_path, 'tar')
for key in vc_paths:
    vc_paths[key] = {
        'root': vc_paths[key],
        'vsvars': os.path.join(vc_paths[key], 'common7/tools/vsvars32.bat'),
    }
python_vc_versions = {
    '2.6': 'vc9',
    '2.7': 'vc9',
    '3.2': 'vc9',
    '3.3': 'vc10',
    '3.4': 'vc10',
}
vc_versions = vc_paths.keys()

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
        with open('.tmp.%s' % archive, 'wb') as f:
            while True:
                chunk = io.read(65536)
                if len(chunk) == 0:
                    break
                f.write(chunk)
        os.rename('.tmp.%s' % archive, archive)

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
    step = step_fn.__name__
    if args:
        step +=  '-' + '-'.join(args)
    if not os.path.exists(state_path):
        os.makedirs(state_path)
    state_file_path = os.path.join(state_path, step)
    if not os.path.exists(state_file_path) or not os.path.exists(target_dir):
        step_fn(*args)
    with open(state_file_path, 'w') as f:
        pass

def untar(basename):
    if os.path.exists(basename):
        shutil.rmtree(basename)
    subprocess.check_call([tar_path, 'xf', '%s.tar.gz' % basename])

def rename_for_vc(basename, vc_version):
    suffixed_dir = '%s-%s' % (basename, vc_version)
    if os.path.exists(suffixed_dir):
        shutil.rmtree(suffixed_dir)
    os.rename(basename, suffixed_dir)
    return suffixed_dir

def build():
    os.environ['PATH'] += ";%s" % git_bin_path
    if not os.path.exists(archives_path):
        os.makedirs(archives_path)
    with in_dir(archives_path):
        def build_zlib(vc_version):
            fetch('http://downloads.sourceforge.net/project/libpng/zlib/%s/zlib-%s.tar.gz' % (zlib_version, zlib_version))
            untar('zlib-%s' % zlib_version)
            zlib_dir = rename_for_vc('zlib-%s' % zlib_version, vc_version)
            with in_dir(zlib_dir):
                with open('doit.bat', 'w') as f:
                    f.write("call \"%s\"\n" % vc_paths[vc_version]['vsvars'])
                    f.write("nmake /f win32/Makefile.msc\n")
                subprocess.check_call(['doit.bat'])
        
        def build_curl(vc_version):
            fetch('http://curl.haxx.se/download/curl-%s.tar.gz' % libcurl_version)
            untar('curl-%s' % libcurl_version)
            curl_dir = rename_for_vc('curl-%s' % libcurl_version, vc_version)
            with in_dir(os.path.join(curl_dir, 'winbuild')):
                with open('doit.bat', 'w') as f:
                    f.write("call \"%s\"\n" % vc_paths[vc_version]['vsvars'])
                    f.write("set include=%%include%%;%s\n" % os.path.join(archives_path, 'zlib-%s-%s' % (zlib_version, vc_version)))
                    f.write("set lib=%%lib%%;%s\n" % os.path.join(archives_path, 'zlib-%s-%s' % (zlib_version, vc_version)))
                    if use_zlib:
                        extra_options = ' WITH_ZLIB=dll'
                    else:
                        extra_options = ''
                    f.write("nmake /f Makefile.vc mode=dll ENABLE_IDN=no%s\n" % extra_options)
                subprocess.check_call(['doit.bat'])
        for vc_version in vc_versions:
            if use_zlib:
                step(build_zlib, (vc_version,), 'zlib-%s-%s' % (zlib_version, vc_version))
            step(build_curl, (vc_version,), 'curl-%s-%s' % (libcurl_version, vc_version))
        
        def prepare_pycurl():
            #fetch('http://pycurl.sourceforge.net/download/pycurl-%s.tar.gz' % pycurl_version)
            if os.path.exists('pycurl-%s' % pycurl_version):
                #shutil.rmtree('pycurl-%s' % pycurl_version)
                subprocess.check_call([rm_path, '-rf', 'pycurl-%s' % pycurl_version])
            #subprocess.check_call([tar_path, 'xf', 'pycurl-%s.tar.gz' % pycurl_version])
            shutil.copytree('c:/dev/pycurl', 'pycurl-%s' % pycurl_version)
        
        def build_pycurl(python_version, target):
            python_path = python_path_template % python_version.replace('.', '')
            vc_version = python_vc_versions[python_version]
            
            with in_dir(os.path.join('pycurl-%s' % pycurl_version)):
                if use_zlib:
                    libcurl_build_name = 'libcurl-vc-x86-release-dll-zlib-dll-ipv6-sspi-spnego-winssl'
                else:
                    libcurl_build_name = 'libcurl-vc-x86-release-dll-ipv6-sspi-spnego-winssl'
                curl_dir = '../curl-%s-%s/builds/%s' % (libcurl_version, vc_version, libcurl_build_name)
                if not os.path.exists('build/lib.win32-%s' % python_version):
                    # exists for building additional targets for the same python version
                    os.makedirs('build/lib.win32-%s' % python_version)
                shutil.copy(os.path.join(curl_dir, 'bin', 'libcurl.dll'), 'build/lib.win32-%s' % python_version)
                with open('doit.bat', 'w') as f:
                    f.write("call \"%s\"\n" % vc_paths[vc_version]['vsvars'])
                    f.write("%s setup.py docstrings\n" % (python_path,))
                    f.write("%s setup.py %s --curl-dir=%s --use-libcurl-dll\n" % (python_path, target, curl_dir))
                subprocess.check_call(['doit.bat'])
                if target == 'bdist':
                    os.rename('dist/pycurl-%s.win32.zip' % pycurl_version, 'dist/pycurl-%s.win32-py%s.zip' % (pycurl_version, python_version))
        
        prepare_pycurl()
        python_releases = ['.'.join(version.split('.')[:2]) for version in python_versions]
        for python_version in python_releases:
            for target in ['bdist', 'bdist_wininst', 'bdist_msi']:
                build_pycurl(python_version, target)

def download_pythons():
    try:
        from urllib.request import urlopen
    except NameError:
        from urllib import urlopen
    
    for version in python_versions:
        if os.path.exists(os.path.join(archives_path, 'python-%s.msi')):
            continue
        print('Downloading %s' % version)
        url = 'http://python.org/ftp/python/%s/python-%s.msi' % (version, version)
        io = urlopen(url)
        data = io.read()
        with open(os.path.join(archives_path, 'python-%s.msi' % version), 'wb') as f:
            f.write(data)

if len(sys.argv) > 1 and sys.argv[1] == 'download':
    download_pythons()
else:
    build()
