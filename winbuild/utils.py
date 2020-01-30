import os.path, subprocess, sys, os, glob, re, contextlib, shutil
try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen

# https://stackoverflow.com/questions/35569042/python-3-ssl-certificate-verify-failed
import ssl
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

# Given a list of paths, return the first path that exists.
def select_existing_path(paths):
    if isinstance(paths, list) or isinstance(paths, tuple):
        for path in paths:
            if os.path.exists(path):
                return path
        return paths[0]
    else:
        return paths

# Find the given binary by its short name in the specified
# list of directories.
def find_in_paths(binary, paths):
    for path in paths:
        if os.path.exists(os.path.join(path, binary)) or os.path.exists(os.path.join(path, binary + '.exe')):
            return os.path.join(path, binary)
    raise Exception('Could not find %s' % binary)

# Executes the specified command, raising an exception if execution failed.
def check_call(cmd):
    try:
        subprocess.check_call(cmd)
    except Exception as e:
        raise Exception('Failed to execute ' + str(cmd) + ': ' + str(type(e)) + ': ' +str(e))

def mkdir_p(path):
    if not os.path.exists(path):
        os.makedirs(path)

def rm_rf(config, path):
    check_call([config.rm_path, '-rf', path])

def cp_r(config, src, dest):
    check_call([config.cp_path, '-r', src, dest])

# Retrieves the file at the given url, saving it in the specified local filesystem path.
# Does nothing if the local path already exists.
def fetch(url, archive=None):
    if archive is None:
        archive = os.path.basename(url)
    if not os.path.exists(archive):
        sys.stdout.write("Fetching %s\n" % url)
        sys.stdout.flush()
        io = urlopen(url)
        tmp_path = os.path.join(os.path.dirname(archive),
            '.%s.part' % os.path.basename(archive))
        with open(tmp_path, 'wb') as f:
            while True:
                chunk = io.read(65536)
                if len(chunk) == 0:
                    break
                f.write(chunk)
        os.rename(tmp_path, archive)
    
# Verifies that provided path exists, and returns it.
def require_file_exists(path):
    if not os.path.exists(path):
        raise Exception('Path %s does not exist!' % path)
    return path

# Converts forward slashes to backslashes.
def fix_slashes(path):
    return path.replace('/', '\\')

# Returns the first path matching the pattern, where pattern is anything the
# standard library glob module recognizes plus {a,b,c} alterations.
# Raises an exception if no paths matched the pattern.
def glob_first(pattern, selector=None):
    # python's glob does not support {}
    final_patterns = []
    pattern_queue = [pattern]
    while pattern_queue:
        pattern = pattern_queue.pop()
        if re.search(r'\{.*}', pattern):
            match = re.match(r'(.*){(.*?)}(.*)', pattern, re.S)
            for variant in match.group(2).split(','):
                pattern_queue.append(match.group(1) + variant + match.group(3))
        else:
            final_patterns.append(pattern)
    for pattern in final_patterns:
        paths = glob.glob(pattern)
        if paths:
            if selector:
                return selector(paths)
            else:
                return paths[0]
    raise Exception("Not found: %s" % pattern)

@contextlib.contextmanager
def in_dir(dir):
    old_cwd = os.getcwd()
    try:
        os.chdir(dir)
        yield
    finally:
        os.chdir(old_cwd)

def untar(config, basename):
    if os.path.exists(basename):
        shutil.rmtree(basename)
    check_call([config.tar_path, 'xf', '%s.tar.gz' % basename])
