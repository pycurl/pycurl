import os.path
from .utils import *
from .builder import *

class OpensslBuilder(StandardBuilder):
    def build(self):
        # another openssl gem:
        # nasm output is redirected to NUL which ends up creating a file named NUL.
        # however being a reserved file name this file is not deletable by
        # ordinary tools.
        nul_file = "openssl-%s-%s\\NUL" % (self.bconf.openssl_version, self.bconf.vc_tag)
        check_call(['rm', '-f', nul_file])
        openssl_dir = self.standard_fetch_extract(
            'https://www.openssl.org/source/openssl-%(my_version)s.tar.gz')
        with in_dir(openssl_dir):
            with self.execute_batch() as b:
                if self.bconf.openssl_version_tuple < (1, 1):
                    # openssl 1.0.2
                    b.add("patch -p0 < %s" % 
                        require_file_exists(os.path.join(config.winbuild_patch_root, 'openssl-fix-crt-1.0.2.patch')))
                elif self.bconf.openssl_version_tuple < (1, 1, 1):
                    # openssl 1.1.0
                    b.add("patch -p0 < %s" %
                        require_file_exists(os.path.join(config.winbuild_patch_root, 'openssl-fix-crt-1.1.0.patch')))
                else:
                    # openssl 1.1.1
                    b.add("patch -p0 < %s" %
                        require_file_exists(os.path.join(config.winbuild_patch_root, 'openssl-fix-crt-1.1.1.patch')))
                if self.bconf.bitness == 64:
                    target = 'VC-WIN64A'
                    batch_file = 'do_win64a'
                else:
                    target = 'VC-WIN32'
                    batch_file = 'do_nasm'

                # msysgit perl has trouble with backslashes used in
                # win64 assembly things in openssl 1.0.2
                # and in x86 assembly as well in openssl 1.1.0;
                # use ActiveState Perl
                if not os.path.exists(config.activestate_perl_bin_path):
                    raise ValueError('activestate_perl_bin_path refers to a nonexisting path')
                if not os.path.exists(os.path.join(config.activestate_perl_bin_path, 'perl.exe')):
                    raise ValueError('No perl binary in activestate_perl_bin_path')
                b.add("set path=%s;%%path%%" % config.activestate_perl_bin_path)
                b.add("perl -v")

                openssl_prefix = os.path.join(os.path.realpath('.'), 'build')
                # Do not want compression:
                # https://en.wikipedia.org/wiki/CRIME
                extras = ['no-comp', 'no-unit-test', 'no-tests', 'no-external-tests']
                if config.openssl_version_tuple >= (1, 1):
                    # openssl 1.1.0
                    # in 1.1.0 the static/shared selection is handled by
                    # invoking the right makefile
                    extras += ['no-shared']
                    
                    # looks like openssl 1.1.0c does not derive
                    # --openssldir from --prefix, like its Configure claims,
                    # and like 1.0.2 does; provide a relative openssl dir
                    # manually
                    extras += ['--openssldir=ssl']
                b.add("perl Configure %s %s --prefix=%s" % (target, ' '.join(extras), openssl_prefix))
                
                if config.openssl_version_tuple < (1, 1):
                    # openssl 1.0.2
                    b.add("call ms\\%s" % batch_file)
                    b.add("nmake -f ms\\nt.mak")
                    b.add("nmake -f ms\\nt.mak install")
                else:
                    # openssl 1.1.0
                    b.add("nmake")
                    b.add("nmake install")
                
                # assemble dist
                b.add('mkdir dist')
                b.add('cp -r build/include build/lib dist')
