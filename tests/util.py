# -*- coding: utf-8 -*-
# vi:ts=4:et

import tempfile
import sys, socket
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

    c = pycurl.COMPILE_LIBCURL_VERSION_NUM
    version = [c >> 16 & 0xFF, c >> 8 & 0xFF, c & 0xFF]
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

            if pycurl.COMPILE_SSL_LIB not in backends:
                raise unittest.SkipTest('SSL backend is %s' % pycurl.COMPILE_SSL_LIB)

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

def only_http2(fn):
    import pycurl

    @functools.wraps(fn)
    def decorated(*args, **kwargs):
        if not pycurl.version_info()[4] & pycurl.VERSION_HTTP2:
            raise unittest.SkipTest('libcurl does not support HTTP version 2')

        return fn(*args, **kwargs)

    return decorated

def only_http3(fn):
    import pycurl

    @functools.wraps(fn)
    def decorated(*args, **kwargs):
        if not pycurl.version_info()[4] & pycurl.VERSION_HTTP3:
            raise unittest.SkipTest('libcurl does not support HTTP version 3')

        return fn(*args, **kwargs)

    return decorated

def only_gssapi(fn):
    import pycurl

    @functools.wraps(fn)
    def decorated(*args, **kwargs):
        if not pycurl.version_info()[4] & pycurl.VERSION_GSSAPI:
            raise unittest.SkipTest('libcurl does not support GSS-API')

        return fn(*args, **kwargs)

    return decorated

def only_tls_srp(fn):
    import pycurl

    @functools.wraps(fn)
    def decorated(*args, **kwargs):
        if not pycurl.version_info()[4] & pycurl.VERSION_TLSAUTH_SRP:
            raise unittest.SkipTest('libcurl does not support TLS-SRP')

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
