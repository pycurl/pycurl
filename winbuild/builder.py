import os, os.path, shutil, sys, subprocess
from .utils import *
from .config import *

class Batch(object):
    def __init__(self, bconf):
        self.bconf = bconf
        self.commands = []
        
        self.add(self.vcvars_cmd)
        self.add('echo on')
        if self.bconf.vc_version == 'vc14':
            # I don't know why vcvars doesn't configure this under vc14
            self.add('set include=%s\\include;%%include%%' % self.bconf.windows_sdk_path)
            if self.bconf.bitness == 32:
                self.add('set lib=%s\\lib;%%lib%%' % self.bconf.windows_sdk_path)
                self.add('set path=%s\\bin;%%path%%' % self.bconf.windows_sdk_path)
            else:
                self.add('set lib=%s\\lib\\x64;%%lib%%' % self.bconf.windows_sdk_path)
                self.add('set path=%s\\bin\\x64;%%path%%' % self.bconf.windows_sdk_path)
        self.add(self.nasm_cmd)
        
        self.add('set path=%s;%%path%%' % self.bconf.extra_bin_paths[self.bconf.bitness]['rc_bin'])
        
    def add(self, cmd):
        self.commands.append(cmd)
        
    # if patch fails to apply hunks, it exits with nonzero code.
    # if patch doesn't find the patch file to apply, it exits with a zero code!
    ERROR_CHECK = 'IF %ERRORLEVEL% NEQ 0 exit %errorlevel%'

    def batch_text(self):
        return ("\n" + self.ERROR_CHECK + "\n").join(self.commands)

    @property
    def vcvars_bitness_parameter(self):
        params = {
            32: 'x86',
            64: 'amd64',
        }
        return params[self.bconf.bitness]

    @property
    def vcvars_relative_path(self):
        return 'vc/vcvarsall.bat'

    @property
    def vc_path(self):
        if self.bconf.vc_version in self.bconf.vc_paths and self.bconf.vc_paths[self.bconf.vc_version]:
            path = self.bconf.vc_paths[self.bconf.vc_version]
            if not os.path.join(path, self.vcvars_relative_path):
                raise Exception('vcvars not found in specified path')
            return path
        else:
            for path in self.bconf.default_vc_paths[self.bconf.vc_version]:
                if os.path.exists(os.path.join(path, self.vcvars_relative_path)):
                    return path
            raise Exception('No usable vc path found')

    @property
    def vcvars_path(self):
        return os.path.join(self.vc_path, self.vcvars_relative_path)

    @property
    def vcvars_cmd(self):
        # https://msdn.microsoft.com/en-us/library/x4d2c09s.aspx
        return "call \"%s\" %s" % (
            self.vcvars_path,
            self.vcvars_bitness_parameter,
        )

    @property
    def nasm_cmd(self):
        return "set path=%s;%%path%%\n" % self.bconf.nasm_path

class Builder(object):
    def __init__(self, **kwargs):
        self.bconf = kwargs.pop('bconf')
        self.use_dlls = False

    @contextlib.contextmanager
    def execute_batch(self):
        batch = Batch(self.bconf)
        yield batch
        with open('doit.bat', 'w') as f:
            f.write(batch.batch_text())
        if False:
            print("Executing:")
            with open('doit.bat', 'r') as f:
                print(f.read())
            sys.stdout.flush()
        rv = subprocess.call(['doit.bat'])
        if rv != 0:
            print("\nFailed to execute the following commands:\n")
            with open('doit.bat', 'r') as f:
                print(f.read())
            sys.stdout.flush()
            exit(3)

class StandardBuilder(Builder):
    @property
    def state_tag(self):
        return self.output_dir_path

    @property
    def bin_path(self):
        return os.path.join(self.bconf.archives_path, self.output_dir_path, 'dist', 'bin')

    @property
    def include_path(self):
        return os.path.join(self.bconf.archives_path, self.output_dir_path, 'dist', 'include')

    @property
    def lib_path(self):
        return os.path.join(self.bconf.archives_path, self.output_dir_path, 'dist', 'lib')

    @property
    def dll_paths(self):
        raise NotImplementedError

    @property
    def builder_name(self):
        return self.__class__.__name__.replace('Builder', '').lower()
        
    @property
    def my_version(self):
        return getattr(self.bconf, '%s_version' % self.builder_name)

    @property
    def output_dir_path(self):
        return '%s-%s-%s' % (self.builder_name, self.my_version, self.bconf.vc_tag)
        
    def standard_fetch_extract(self, url_template):
        url = url_template % dict(
            my_version=self.my_version,
        )
        fetch(url)
        archive_basename = os.path.basename(url)
        archive_name = archive_basename.replace('.tar.gz', '')
        untar(self.bconf, archive_name)
        
        suffixed_dir = self.output_dir_path
        if os.path.exists(suffixed_dir):
            shutil.rmtree(suffixed_dir)
        os.rename(archive_name, suffixed_dir)
        return suffixed_dir
