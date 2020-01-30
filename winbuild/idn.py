from .utils import *
from .builder import *

class LibidnBuilder(StandardBuilder):
    def build(self):
        libidn_dir = self.standard_fetch_extract(
            'https://ftp.gnu.org/gnu/libidn/libidn-%(my_version)s.tar.gz')
        with in_dir(libidn_dir):
            with self.execute_batch() as b:
                b.add("env LD=link bash ./configure")
