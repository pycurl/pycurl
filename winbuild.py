# work directory for downloading dependencies and building everything
root = 'c:/dev/build-pycurl'
# where msysgit is installed
git_root = 'c:/program files/git'
# which versions of python to build against
python_versions = ['2.6', '2.7']
# where pythons are installed
python_path_template = 'c:/python%s/python'
# which version of libcurl to use, will be downloaded from the internet
libcurl_version = '7.34.0'
# pycurl version to build, we should know this ourselves
pycurl_version = '7.19.0.3'

import os, os.path, sys, subprocess, shutil, contextlib

archives_path = os.path.join(root, 'archives')
state_path = os.path.join(root, 'state')
git_bin_path = os.path.join(git_root, 'bin')
git_path = os.path.join(git_bin_path, 'git')
rm_path = os.path.join(git_bin_path, 'rm')
tar_path = os.path.join(git_bin_path, 'tar')

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
def step(step_fn):
    step = step_fn.__name__
    if not os.path.exists(state_path):
        os.makedirs(state_path)
    state_file_path = os.path.join(state_path, step)
    if not os.path.exists(state_file_path):
        step_fn()
    with open(state_file_path, 'w') as f:
        pass
        
def work():
    os.environ['PATH'] += ";%s" % git_bin_path
    if not os.path.exists(archives_path):
        os.makedirs(archives_path)
    with in_dir(archives_path):
        def build_curl():
            fetch('http://curl.haxx.se/download/curl-%s.tar.gz' % libcurl_version)
            if os.path.exists('curl-%s' % libcurl_version):
                shutil.rmtree('curl-%s' % libcurl_version)
            subprocess.check_call([tar_path, 'xf', 'curl-%s.tar.gz' % libcurl_version])
            with in_dir(os.path.join('curl-%s' % libcurl_version, 'winbuild')):
                subprocess.check_call(['nmake', '/f', 'Makefile.vc', 'mode=static', 'ENABLE_IDN=no'])
                subprocess.check_call(['nmake', '/f', 'Makefile.vc', 'mode=dll', 'ENABLE_IDN=no'])
        step(build_curl)
        
        def prepare_pycurl():
            #fetch('http://pycurl.sourceforge.net/download/pycurl-%s.tar.gz' % pycurl_version)
            if os.path.exists('pycurl-%s' % pycurl_version):
                #shutil.rmtree('pycurl-%s' % pycurl_version)
                subprocess.check_call([rm_path, '-rf', 'pycurl-%s' % pycurl_version])
            #subprocess.check_call([tar_path, 'xf', 'pycurl-%s.tar.gz' % pycurl_version])
            shutil.copytree('c:/dev/pycurl', 'pycurl-%s' % pycurl_version)
        
        def build_pycurl(python_version, target):
            python_path = python_path_template % python_version.replace('.', '')
            
            with in_dir(os.path.join('pycurl-%s' % pycurl_version)):
                libcurl_build_name = 'libcurl-vc-x86-release-dll-ipv6-sspi-spnego-winssl'
                curl_dir = '../curl-%s/builds/%s' % (libcurl_version, libcurl_build_name)
                if not os.path.exists('build/lib.win32-%s' % python_version):
                    # exists for building additional targets for the same python version
                    os.makedirs('build/lib.win32-%s' % python_version)
                shutil.copy(os.path.join(curl_dir, 'bin', 'libcurl.dll'), 'build/lib.win32-%s' % python_version)
                subprocess.check_call([python_path, 'setup.py', target, '--curl-dir=%s' % curl_dir])
                if target == 'bdist':
                    os.rename('dist/pycurl-%s.win32.zip' % pycurl_version, 'dist/pycurl-%s.win32-py%s.zip' % (pycurl_version, python_version))
        
        prepare_pycurl()
        for python_version in python_versions:
            for target in ['bdist', 'bdist_wininst', 'bdist_msi']:
                build_pycurl(python_version, target)

work()
