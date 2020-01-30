import shutil
from .builder import *

class Nghttp2Builder(StandardBuilder):
    def build(self):
        nghttp2_dir = self.standard_fetch_extract(
            'https://github.com/nghttp2/nghttp2/releases/download/v%(my_version)s/nghttp2-%(my_version)s.tar.gz')
                
        with in_dir(os.path.join(nghttp2_dir, 'lib')):
            with self.execute_batch() as b:
                
                b.add('"%s" -f Makefile.msvc' % self.bconf.gmake_path)
                
                # assemble dist
                b.add('mkdir ..\\dist ..\\dist\\include ..\\dist\\include\\nghttp2 ..\\dist\\lib')
                b.add('cp msvc_obj/*.lib ../dist/lib')
                b.add('cp includes/nghttp2/*.h ../dist/include/nghttp2')
            
            # libcurl expects nghttp2_static.lib apparently, the makefile
            # gives a different name to the static library
            if not os.path.exists('../dist/lib/nghttp2_static.lib'):
                shutil.copy('../dist/lib/nghttp2-static.lib', '../dist/lib/nghttp2_static.lib')
