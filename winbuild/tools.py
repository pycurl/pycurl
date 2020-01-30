from .config import *

def short_python_versions(python_versions):
    return ['.'.join(python_version.split('.')[:2])
        for python_version in python_versions]

def needed_vc_versions(config, python_versions):
    return [vc_version for vc_version in config.vc_paths.keys()
        if vc_version in [
            PYTHON_VC_VERSIONS[short_python_version]
            for short_python_version in short_python_versions(python_versions)]]
