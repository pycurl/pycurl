import os.path
from .utils import *
from .builder import *

class ZlibBuilder(StandardBuilder):
    def build(self):
        zlib_dir = self.standard_fetch_extract(
            'http://downloads.sourceforge.net/project/libpng/zlib/%(my_version)s/zlib-%(my_version)s.tar.gz')
        with in_dir(zlib_dir):
            with self.execute_batch() as b:
                b.add("nmake /f win32/Makefile.msc")
                # libcurl loves its _a suffixes on static library names
                b.add("cp zlib.lib zlib_a.lib")
                
                # assemble dist
                b.add('mkdir dist dist\\include dist\\lib dist\\bin')
                b.add('cp *.lib *.exp dist/lib')
                b.add('cp *.dll dist/bin')
                b.add('cp *.h dist/include')

    @property
    def dll_paths(self):
        return [
            os.path.join(self.bin_path, 'zlib1.dll'),
        ]
