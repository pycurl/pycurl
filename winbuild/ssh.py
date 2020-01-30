from .utils import *
from .builder import *

class Libssh2Builder(StandardBuilder):
    def build(self):
        libssh2_dir = self.standard_fetch_extract(
            'http://www.libssh2.org/download/libssh2-%(my_version)s.tar.gz')
        with in_dir(libssh2_dir):
            with self.execute_batch() as b:
                if self.bconf.libssh2_version_tuple < (1, 8, 0) and self.bconf.vc_version == 'vc14':
                    b.add("patch -p0 < %s" %
                        require_file_exists(os.path.join(config.winbuild_patch_root, 'libssh2-vs2015.patch')))
                zlib_builder = ZlibBuilder(bconf=self.bconf)
                openssl_builder = OpensslBuilder(bconf=self.bconf)
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
                b.add("nmake -f NMakefile")
                # libcurl loves its _a suffixes on static library names
                b.add("cp Release\\src\\libssh2.lib Release\\src\\libssh2_a.lib")
                
                # assemble dist
                b.add('mkdir dist dist\\include dist\\lib')
                b.add('cp Release/src/*.lib dist/lib')
                b.add('cp -r include dist')
