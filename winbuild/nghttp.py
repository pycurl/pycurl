import shutil
from .builder import *

class Nghttp2Builder(StandardBuilder):
    CMAKE_GENERATORS = {
        # Thanks cmake for requiring both version number and year,
        # necessitating this additional map
        'vc9': 'Visual Studio 9 2008',
        'vc14': 'Visual Studio 14 2015',
    }
    
    def build(self):
        nghttp2_dir = self.standard_fetch_extract(
            'https://github.com/nghttp2/nghttp2/releases/download/v%(my_version)s/nghttp2-%(my_version)s.tar.gz')
                
        # nghttp2 uses stdint.h which msvc9 does not ship.
        # Amazingly, nghttp2 can seemingly build successfully without this
        # file existing, but libcurl build subsequently fails
        # when it tries to include stdint.h.
        # Well, the reason why nghttp2 builds correctly is because it is built
        # with the wrong compiler - msvc14 when 9 and 14 are both installed.
        # nghttp2 build with msvc9 does fail without stdint.h existing.
        if self.bconf.vc_version == 'vc9':
            # https://stackoverflow.com/questions/126279/c99-stdint-h-header-and-ms-visual-studio
            fetch('https://raw.githubusercontent.com/mattn/gntp-send/master/include/msinttypes/stdint.h')
            with in_dir(nghttp2_dir):
                shutil.copy('../stdint.h', 'lib/includes/stdint.h')
        
        with in_dir(nghttp2_dir):
            generator = self.CMAKE_GENERATORS[self.bconf.vc_version]
            with self.execute_batch() as b:
                # Workaround for VCTargetsPath issue that looks like this:
                # C:\dev\build-pycurl\archives\nghttp2-1.40.0-vc14-32\CMakeFiles\3.16.3\VCTargetsPath.vcxproj(14,2): error MSB4019: The imported project "C:\Microsoft.Cpp.Default.props" was not found. Confirm that the path in the <Import> declaration is correct, and that the file exists on disk.
                #
                # Many solutions proposed on SO, including:
                # https://stackoverflow.com/questions/41695251/c-microsoft-cpp-default-props-was-not-found
                # https://stackoverflow.com/questions/16092169/why-does-msbuild-look-in-c-for-microsoft-cpp-default-props-instead-of-c-progr
                if not os.path.exists(self.bconf.vc_targets_path):
                    raise ValueError("VCTargetsPath does not exist: %s" % self.bconf.vc_targets_path)
                b.add('SET VCTargetsPath=%s' % self.bconf.vc_targets_path)
                
                # The msbuild.exe in path could be v4.0 from .net sdk, whereas the
                # vctargetspath ends up referencing the msbuild from visual studio...
                # Put the visual studio msbuild into the path first.
                if self.bconf.bitness == 64:
                    msbuild_bin_path = os.path.join(self.bconf.msbuild_bin_path, 'amd64')
                else:
                    msbuild_bin_path = self.bconf.msbuild_bin_path
                b.add("set path=%s;%%path%%" % msbuild_bin_path)
                
                # When performing 64-bit build, ucrtd.lib is not in library path for whatever reason. Sigh.
                # Superseded by https://stackoverflow.com/questions/56145118/cmake-cannot-open-ucrtd-lib instructions below.
                if self.bconf.bitness == 64 and False:
                    windows_sdk_lib_path = glob_first("c:\\Program Files (x86)\\Windows Kits\\10\\Lib\\*\\ucrt\\x64")
                    b.add('set lib=%s;%%lib%%' % windows_sdk_lib_path)
                
                parts = [
                    '"%s"' % self.bconf.cmake_path,
                    # I don't know if this does anything, build type/config
                    # must be specified with --build option below.
                    '-DCMAKE_BUILD_TYPE=Release',
                    # This configures libnghttp2 only which is what we want.
                    # However, configure step still complains about all of the
                    # missing dependencies for nghttp2 server.
                    # And there is no indication whatsoever from configure step
                    # that this option is enabled, or that the missing
                    # dependency complaints can be ignored.
                    '-DENABLE_LIB_ONLY=1',
                    # This is required to get a static library built.
                    # However, even with this turned on there is still a DLL
                    # built - without an import library for it.
                    '-DENABLE_STATIC_LIB=1',
                    # And cmake ignores all visual studio environment variables
                    # and uses the newest compiler by default, which is great
                    # if one doesn't care what compiler their code is compiled with.
                    # https://stackoverflow.com/questions/6430251/what-is-the-default-generator-for-cmake-in-windows
                    '-G', '"%s"' % generator,
                ]
                
                # Cmake also couldn't care less about the bitness I have configured in the
                # environment since it ignores the environment entirely.
                # Educate it on the required bitness by hand.
                # https://stackoverflow.com/questions/28350214/how-to-build-x86-and-or-x64-on-windows-from-command-line-with-cmake#28370892
                #
                # New strategy:
                # https://cmake.org/cmake/help/v3.14/generator/Visual%20Studio%2014%202015.html
                if self.bconf.bitness == 64 and False:
                    parts += ['-A', 'x64']
                    
                    # And it does its own windows sdk selection, apparently, and botches it.
                    # https://stackoverflow.com/questions/56145118/cmake-cannot-open-ucrtd-lib
                    # TODO figure out which version is needed here, 8.1 or 10.0 or 10.0.10240.0
                    parts.append('-DCMAKE_SYSTEM_VERSION=8.1')
                
                b.add('%s .' % ' '.join(parts))
                b.add(' '.join([
                    '"%s"' % self.bconf.cmake_path,
                    '--build', '.',
                    # this is what produces a release build
                    '--config', 'Release',
                    # this builds the static library.
                    # without this option cmake configures itself to be capable
                    # of building a static library but sometimes builds a DLL
                    # and sometimes builds a static library
                    # depending on compiler in use (vc9/vc14) or, possibly,
                    # phase of the moon.
                    '--target', 'nghttp2_static',
                ]))
                
                # assemble dist
                b.add('mkdir dist dist\\include dist\\include\\nghttp2 dist\\lib')
                b.add('cp lib/Release/*.lib dist/lib')
                b.add('cp lib/includes/nghttp2/*.h dist/include/nghttp2')
                if self.bconf.vc_version == 'vc9':
                    # stdint.h
                    b.add('cp lib/includes/*.h dist/include')
            
            # libcurl expects nghttp2_static.lib apparently, and depending on nghttp2 version/configuration(?)
            # the library name is sometimes nghttp2.lib
            if not os.path.exists('lib/Release/nghttp2_static.lib'):
                shutil.copy('lib/Release/nghttp2.lib', 'lib/Release/nghttp2_static.lib')
