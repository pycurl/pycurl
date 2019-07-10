from distutils.command import build_ext as _build_ext
from distutils.spawn import spawn as _spawn
import threading

sources = [
    'docstrings.c',
    'easy.c',
    'easycb.c',
    'easyinfo.c',
    'easyopt.c',
    'easyperform.c',
    'module.c',
    'multi.c',
    'oscompat.c',
    'pythoncompat.c',
    'share.c',
    'stringcompat.c',
    'threadsupport.c',
    'util.c',
]

compile_threads = []

event = threading.Event()


def compile(dry_run, cmd):
    _spawn(cmd, dry_run=dry_run)
    compile_threads.remove(threading.currentThread())
    if not compile_threads and not sources:
        event.set()


def spawn(self, cmd):
    for arg in cmd:
        if 'allpycurl.c' in arg:
            _spawn(cmd, dry_run=self.dry_run)
            return

    for source in sources:
        for arg in cmd:
            if source in arg:
                t = threading.Thread(target=compile, args=(self.dry_run, cmd))
                t.daemon = True
                compile_threads.append(t)
                t.start()
                sources.remove(source)
                break

    if not sources:
        event.wait()


class build_ext(_build_ext.build_ext):

    def build_extension(self, ext):
        def do(cmd):
            spawn(self.compiler, cmd)

        self.compiler.spawn = do
        _build_ext.build_ext.build_extension(self, ext)
