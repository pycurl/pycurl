from .utils import *
from .builder import *

class LibiconvBuilder(StandardBuilder):
    def build(self):
        libiconv_dir = self.standard_fetch_extract(
            'https://ftp.gnu.org/pub/gnu/libiconv/libiconv-%(my_version)s.tar.gz')
        with in_dir(libiconv_dir):
            with self.execute_batch() as b:
                b.add("env LD=link bash ./configure")
                b.add(config.gmake_path)
