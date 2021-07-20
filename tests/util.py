# -*- coding: utf-8 -*-
# vi:ts=4:et

import tempfile
import os, sys, socket
import time as _time
import functools
import unittest

py3 = sys.version_info[0] == 3

# python 2/3 compatibility
if py3:
    from io import StringIO, BytesIO

    # borrowed from six
    def b(s):
        '''Byte literal'''
        return s.encode("latin-1")
    def u(s):
        '''Text literal'''
        return s
    text_type = str
    binary_type = bytes

    long_int = int
else:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO
    BytesIO = StringIO

    # pyflakes workaround
    # https://github.com/kevinw/pyflakes/issues/13
    # https://bugs.launchpad.net/pyflakes/+bug/1308508/comments/3
    if False:
        unicode = object

    # borrowed from six
    def b(s):
        '''Byte literal'''
        return s
    # Workaround for standalone backslash
    def u(s):
        '''Text literal'''
        return unicode(s.replace(r'\\', r'\\\\'), "unicode_escape")
    text_type = unicode
    binary_type = str

    if False:
        # pacify pyflakes
        long = int
    long_int = long

def version_less_than_spec(version_tuple, spec_tuple):
    # spec_tuple may have 2 elements, expect version_tuple to have 3 elements
    assert len(version_tuple) >= len(spec_tuple)
    for i in range(len(spec_tuple)):
        if version_tuple[i] < spec_tuple[i]:
            return True
        if version_tuple[i] > spec_tuple[i]:
            return False
    return False

def pycurl_version_less_than(*spec):
    import pycurl

    version = [int(part) for part in pycurl.version_info()[1].split('-')[0].split('.')]
    return version_less_than_spec(version, spec)

def only_python2(fn):
    @functools.wraps(fn)
    def decorated(*args, **kwargs):
        if sys.version_info[0] >= 3:
            raise unittest.SkipTest('python >= 3')

        return fn(*args, **kwargs)

    return decorated

def only_python3(fn):
    @functools.wraps(fn)
    def decorated(*args, **kwargs):
        if sys.version_info[0] < 3:
            raise unittest.SkipTest('python < 3')

        return fn(*args, **kwargs)

    return decorated

def min_python(major, minor):
    def decorator(fn):
        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            if sys.version_info[0:2] < (major, minor):
                raise unittest.SkipTest('python < %d.%d' % (major, minor))

            return fn(*args, **kwargs)

        return decorated

    return decorator

def min_libcurl(major, minor, patch):
    def decorator(fn):
        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            if pycurl_version_less_than(major, minor, patch):
                raise unittest.SkipTest('libcurl < %d.%d.%d' % (major, minor, patch))

            return fn(*args, **kwargs)

        return decorated

    return decorator

def removed_in_libcurl(major, minor, patch):
    def decorator(fn):
        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            if not pycurl_version_less_than(major, minor, patch):
                raise unittest.SkipTest('libcurl >= %d.%d.%d' % (major, minor, patch))

            return fn(*args, **kwargs)

        return decorated

    return decorator

def only_ssl(fn):
    import pycurl

    @functools.wraps(fn)
    def decorated(*args, **kwargs):
        # easier to check that pycurl supports https, although
        # theoretically it is not the same test.
        # pycurl.version_info()[8] is a tuple of protocols supported by libcurl
        if 'https' not in pycurl.version_info()[8]:
            raise unittest.SkipTest('libcurl does not support ssl')

        return fn(*args, **kwargs)

    return decorated

def only_telnet(fn):
    import pycurl

    @functools.wraps(fn)
    def decorated(*args, **kwargs):
        # pycurl.version_info()[8] is a tuple of protocols supported by libcurl
        if 'telnet' not in pycurl.version_info()[8]:
            raise unittest.SkipTest('libcurl does not support telnet')

        return fn(*args, **kwargs)

    return decorated

def only_ssl_backends(*backends):
    def decorator(fn):
        import pycurl

        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            # easier to check that pycurl supports https, although
            # theoretically it is not the same test.
            # pycurl.version_info()[8] is a tuple of protocols supported by libcurl
            if 'https' not in pycurl.version_info()[8]:
                raise unittest.SkipTest('libcurl does not support ssl')

            # XXX move to pycurl library
            if 'OpenSSL/' in pycurl.version:
                current_backend = 'openssl'
            elif 'GnuTLS/' in pycurl.version:
                current_backend = 'gnutls'
            elif 'NSS/' in pycurl.version:
                current_backend = 'nss'
            else:
                current_backend = 'none'
            if current_backend not in backends:
                raise unittest.SkipTest('SSL backend is %s' % current_backend)

            return fn(*args, **kwargs)

        return decorated
    return decorator

def only_ipv6(fn):
    import pycurl

    @functools.wraps(fn)
    def decorated(*args, **kwargs):
        if not pycurl.version_info()[4] & pycurl.VERSION_IPV6:
            raise unittest.SkipTest('libcurl does not support ipv6')

        return fn(*args, **kwargs)

    return decorated

def only_unix(fn):
    @functools.wraps(fn)
    def decorated(*args, **kwargs):
        if sys.platform == 'win32':
            raise unittest.SkipTest('Unix only')

        return fn(*args, **kwargs)

    return decorated

def guard_unknown_libcurl_option(fn):
    '''Converts curl error 48, CURLE_UNKNOWN_OPTION, into a SkipTest
    exception. This is meant to be used with tests exercising libcurl
    features that depend on external libraries, such as libssh2/gssapi,
    where libcurl does not provide a way of detecting whether the
    required libraries were compiled against.'''

    import pycurl

    @functools.wraps(fn)
    def decorated(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except pycurl.error:
            exc = sys.exc_info()[1]
            # E_UNKNOWN_OPTION is available as of libcurl 7.21.5
            if hasattr(pycurl, 'E_UNKNOWN_OPTION') and exc.args[0] == pycurl.E_UNKNOWN_OPTION:
                raise unittest.SkipTest('CURLE_UNKNOWN_OPTION, skipping test')

    return decorated

try:
    create_connection = socket.create_connection
except AttributeError:
    # python 2.5
    def create_connection(netloc, timeout=None):
        # XXX ipv4 only
        s = socket.socket()
        if timeout is not None:
            s.settimeout(timeout)
        s.connect(netloc)
        return s

def wait_for_network_service(netloc, check_interval, num_attempts):
    ok = False
    for i in range(num_attempts):
        try:
            conn = create_connection(netloc, check_interval)
        except socket.error:
            #e = sys.exc_info()[1]
            _time.sleep(check_interval)
        else:
            conn.close()
            ok = True
            break
    return ok

#
# prepare sys.path in case we are still in the build directory
# see also: distutils/command/build.py (build_platlib)
#

def get_sys_path(p=None):
    if p is None:
        p = sys.path
    p = p[:]
    try:
        from distutils.util import get_platform
    except ImportError:
        return p
    p0 = ""
    if p:
        p0 = p[0]
    #
    plat = get_platform()
    plat_specifier = "%s-%s" % (plat, sys.version[:3])
    ##print plat, plat_specifier
    #
    for prefix in (p0, os.curdir, os.pardir,):
        if not prefix:
            continue
        d = os.path.join(prefix, "build")
        for subdir in ("lib", "lib." + plat_specifier, "lib." + plat):
            dir = os.path.normpath(os.path.join(d, subdir))
            if os.path.isdir(dir):
                if dir not in p:
                    p.insert(1, dir)
    #
    return p


def DefaultCurl():
    import pycurl

    curl = pycurl.Curl()
    curl.setopt(curl.FORBID_REUSE, True)
    return curl

def DefaultCurlLocalhost(port):
    '''This is a default curl with localhost -> 127.0.0.1 name mapping
    on windows systems, because they don't have it in the hosts file.
    '''
    
    curl = DefaultCurl()
    
    if sys.platform == 'win32':
        curl.setopt(curl.RESOLVE, ['localhost:%d:127.0.0.1' % port])
    
    return curl

def with_real_write_file(fn):
    @functools.wraps(fn)
    def wrapper(*args):
        with tempfile.NamedTemporaryFile() as f:
            return fn(*(list(args) + [f.file]))
    return wrapper
