import os.path, shutil, zipfile
from .builder import *
from .utils import *
from .curl import *

class PycurlBuilder(Builder):
    def __init__(self, **kwargs):
        self.python_release = kwargs.pop('python_release')
        super(PycurlBuilder, self).__init__(**kwargs)
        # vc_version is specified externally for bconf/BuildConfig
        assert self.bconf.vc_version == PYTHON_VC_VERSIONS[self.python_release]

    @property
    def python_path(self):
        if self.bconf.build_wheels:
            python_path = os.path.join(self.bconf.archives_path, 'venv-%s-%s' % (self.python_release, self.bconf.bitness), 'scripts', 'python')
        else:
            python_path = PythonBinary(self.python_release, self.bconf.bitness).executable_path
        return python_path

    @property
    def platform_indicator(self):
        platform_indicators = {32: 'win32', 64: 'win-amd64'}
        return platform_indicators[self.bconf.bitness]

    def build(self, targets):
        libcurl_builder = LibcurlBuilder(bconf=self.bconf)
        libcurl_dir = os.path.join(os.path.abspath(libcurl_builder.output_dir_path), 'dist')
        dll_paths = libcurl_builder.dll_paths
        if self.bconf.use_zlib:
            zlib_builder = ZlibBuilder(bconf=self.bconf)
            dll_paths += zlib_builder.dll_paths
        dll_paths = [os.path.abspath(dll_path) for dll_path in dll_paths]
        with in_dir(self.build_dir_name):
            dest_lib_path = 'build/lib.%s-%s' % (self.platform_indicator,
                self.python_release)
            # exists for building additional targets for the same python version
            mkdir_p(dest_lib_path)
            if self.use_dlls:
                for dll_path in dll_paths:
                    shutil.copy(dll_path, dest_lib_path)
            with self.execute_batch() as b:
                b.add("%s setup.py docstrings" % (self.python_path,))
                if self.use_dlls:
                    libcurl_arg = '--use-libcurl-dll'
                else:
                    libcurl_arg = '--libcurl-lib-name=libcurl_a.lib'
                if self.bconf.use_openssl:
                    libcurl_arg += ' --with-openssl'
                    if self.bconf.openssl_version_tuple >= (1, 1):
                        libcurl_arg += ' --openssl-lib-name=""'
                    openssl_builder = OpensslBuilder(bconf=self.bconf)
                    b.add("set include=%%include%%;%s" % openssl_builder.include_path)
                    b.add("set lib=%%lib%%;%s" % openssl_builder.lib_path)
                #if build_wheels:
                    #b.add("call %s" % os.path.join('..', 'venv-%s-%s' % (self.python_release, self.bconf.bitness), 'Scripts', 'activate'))
                if self.bconf.build_wheels:
                    targets = targets + ['bdist_wheel']
                if self.bconf.libcurl_version_tuple >= (7, 60, 0):
                    # As of 7.60.0 libcurl does not include its dependencies into
                    # its static libraries.
                    # libcurl_a.lib in 7.59.0 is 30 mb.
                    # libcurl_a.lib in 7.60.0 is 2 mb.
                    # https://github.com/curl/curl/pull/2474 is most likely culprit.
                    # As a result we need to specify all of the libraries that
                    # libcurl depends on here, plus the library paths,
                    # plus even windows standard libraries for good measure.
                    if self.bconf.use_zlib:
                        zlib_builder = ZlibBuilder(bconf=self.bconf)
                        libcurl_arg += ' --link-arg=/LIBPATH:%s' % zlib_builder.lib_path
                        libcurl_arg += ' --link-arg=zlib.lib'
                    if self.bconf.use_openssl:
                        openssl_builder = OpensslBuilder(bconf=self.bconf)
                        libcurl_arg += ' --link-arg=/LIBPATH:%s' % openssl_builder.lib_path
                        # openssl 1.1
                        libcurl_arg += ' --link-arg=libcrypto.lib'
                        libcurl_arg += ' --link-arg=libssl.lib'
                        libcurl_arg += ' --link-arg=crypt32.lib'
                        libcurl_arg += ' --link-arg=advapi32.lib'
                    if self.bconf.use_cares:
                        cares_builder = CaresBuilder(bconf=self.bconf)
                        libcurl_arg += ' --link-arg=/LIBPATH:%s' % cares_builder.lib_path
                        libcurl_arg += ' --link-arg=libcares.lib'
                    if self.bconf.use_libssh2:
                        libssh2_builder = Libssh2Builder(bconf=self.bconf)
                        libcurl_arg += ' --link-arg=/LIBPATH:%s' % libssh2_builder.lib_path
                        libcurl_arg += ' --link-arg=libssh2.lib'
                    if self.bconf.use_nghttp2:
                        nghttp2_builder = Nghttp2Builder(bconf=self.bconf)
                        libcurl_arg += ' --link-arg=/LIBPATH:%s' % nghttp2_builder.lib_path
                        libcurl_arg += ' --link-arg=nghttp2_static.lib'
                    if self.bconf.vc_version == 'vc9':
                        # this is for normaliz.lib
                        libcurl_builder = LibcurlBuilder(bconf=self.bconf)
                        libcurl_arg += ' --link-arg=/LIBPATH:%s' % libcurl_builder.lib_path
                    # We always use normaliz.lib, but it may come from
                    # "standard" msvc location or from libcurl's lib dir for msvc9
                    libcurl_arg += ' --link-arg=normaliz.lib'
                    libcurl_arg += ' --link-arg=user32.lib'
                b.add("%s setup.py %s --curl-dir=%s %s" % (
                    self.python_path, ' '.join(targets), libcurl_dir, libcurl_arg))
            # Fixing of bizarre paths in created zip archives,
            # no longer relevant because we only keep wheels
            if False and 'bdist' in targets:
                zip_basename_orig = 'pycurl-%s.%s.zip' % (
                    self.bconf.pycurl_version, self.platform_indicator)
                zip_basename_new = 'pycurl-%s.%s-py%s.zip' % (
                    self.bconf.pycurl_version, self.platform_indicator, self.python_release)
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
    
    @property
    def build_dir_name(self):
        return 'pycurl-%s-py%s-%s' % (self.bconf.pycurl_version, self.python_release, self.bconf.vc_tag)
    
    def prepare_tree(self):
        #fetch('https://dl.bintray.com/pycurl/pycurl/pycurl-%s.tar.gz' % pycurl_version)
        if os.path.exists(self.build_dir_name):
            # shutil.rmtree is incapable of removing .git directory because it contains
            # files marked read-only (tested on python 2.7 and 3.6)
            #shutil.rmtree('pycurl-%s' % config.pycurl_version)
            rm_rf(self.bconf, self.build_dir_name)
        #check_call([tar_path, 'xf', 'pycurl-%s.tar.gz' % pycurl_version])
        shutil.copytree('c:/dev/pycurl', self.build_dir_name)
