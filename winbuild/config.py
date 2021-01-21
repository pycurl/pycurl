import os
from .utils import *
from .pythons import *

class ExtendedConfig:
    '''Global configuration that specifies what the entire process will do.
    
    Unlike Config, this class contains also various derived properties
    for convenience.
    '''
    
    def __init__(self, user_config, **kwargs):
        for k in user_config:
            self.__dict__[k] = user_config[k]
        for k in kwargs:
            setattr(self, k, kwargs[k])

    # These are defaults, overrides can be specified as vc_paths in Config above
    default_vc_paths = {
        # where msvc 9 is installed, for python 2.6-3.2
        'vc9': [
            'c:/program files (x86)/microsoft visual studio 9.0',
            'c:/program files/microsoft visual studio 9.0',
        ],
        # where msvc 10 is installed, for python 3.3-3.4
        'vc10': [
            'c:/program files (x86)/microsoft visual studio 10.0',
            'c:/program files/microsoft visual studio 10.0',
        ],
        # where msvc 14 is installed, for python 3.5-3.9
        'vc14': [
            'c:/program files (x86)/microsoft visual studio 14.0',
            'c:/program files/microsoft visual studio 14.0',
        ],
    }
            
    @property
    def nasm_path(self):
        return select_existing_path(self.__dict__['nasm_path'])
        
    @property
    def activestate_perl_path(self):
        return select_existing_path(self.__dict__['activestate_perl_path'])
        
    @property
    def archives_path(self):
        return os.path.join(self.root, 'archives')
        
    @property
    def state_path(self):
        return os.path.join(self.root, 'state')
        
    @property
    def git_bin_path(self):
        #git_bin_path = os.path.join(git_root, 'bin')
        return ''
        
    @property
    def git_path(self):
        return os.path.join(self.git_bin_path, 'git')
        
    @property
    def rm_path(self):
        return find_in_paths('rm', self.msysgit_bin_paths)
        
    @property
    def cp_path(self):
        return find_in_paths('cp', self.msysgit_bin_paths)
        
    @property
    def sed_path(self):
        return find_in_paths('sed', self.msysgit_bin_paths)
        
    @property
    def tar_path(self):
        return find_in_paths('tar', self.msysgit_bin_paths)
        
    @property
    def activestate_perl_bin_path(self):
        return os.path.join(self.activestate_perl_path, 'bin')
        
    @property
    def winbuild_patch_root(self):
        return os.path.join(self.winbuild_root, 'winbuild')

    @property
    def openssl_version_tuple(self):
        return tuple(
            int(part) if part < 'a' else part
            for part in re.sub(r'([a-z])', r'.\1', self.openssl_version).split('.')
        )

    @property
    def libssh2_version_tuple(self):
        return tuple(int(part) for part in self.libssh2_version.split('.'))

    @property
    def cares_version_tuple(self):
        return tuple(int(part) for part in self.cares_version.split('.'))

    @property
    def libcurl_version_tuple(self):
        return tuple(int(part) for part in self.libcurl_version.split('.'))

    @property
    def python_releases(self):
        return [PythonRelease('.'.join(version.split('.')[:2]))
            for version in self.python_versions]

    @property
    def extra_bin_paths(self):
        paths = {32: {}, 64: {}}

        # When using visual studio 2019 community, rc.exe is not in path for whatever reason - handle this manually.
        paths[32]['rc_bin'] = os.path.dirname(glob_first('c:/{program files,program files (x86)}/windows kits/*/bin/*/x86/rc.exe'))
        paths[64]['rc_bin'] = os.path.dirname(glob_first('c:/{program files,program files (x86)}/windows kits/*/bin/*/x64/rc.exe'))
        
        return paths

BITNESSES = (32, 64)

PYTHON_VC_VERSIONS = {
    '2.6': 'vc9',
    '2.7': 'vc9',
    '3.2': 'vc9',
    '3.3': 'vc10',
    '3.4': 'vc10',
    '3.5': 'vc14',
    '3.6': 'vc14',
    '3.7': 'vc14',
    '3.8': 'vc14',
    '3.9': 'vc14',
}

class BuildConfig:
    '''Parameters for a particular build configuration.
    
    Unlike ExtendedConfig, this class fixes bitness and Python version.
    '''
    
    def __init__(self, ext_config, **kwargs):
        for k in dir(ext_config):
            if k.startswith('_'):
                continue
            self.__dict__[k] = getattr(ext_config, k)
        for k in kwargs:
            setattr(self, k, kwargs[k])
        
        assert self.bitness
        assert self.bitness in (32, 64)
        assert self.vc_version

    @property
    def vc_tag(self):
        return '%s-%s' % (self.vc_version, self.bitness)
