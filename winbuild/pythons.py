
class PythonRelease(str):
    @property
    def dotless(self):
        return self.replace('.', '')

class PythonVersion(str):
    @property
    def release(self):
        return PythonRelease('.'.join(self.split('.')[:2]))

class PythonBinary(object):
    def __init__(self, python_release, bitness):
        self.python_release = python_release
        self.bitness = bitness

    def executable_path(self, config):
        return config.python_path_template % dict(
            python_release=self.python_release.dotless,
            bitness=self.bitness)
