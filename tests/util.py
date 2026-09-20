# vi:ts=4:et

import contextlib
import functools
import gc
import os
import socket
import sys
import tempfile
import time as _time
import weakref

import pytest

def b(s):
    """Byte literal"""
    return s.encode("latin-1")


def u(s):
    """Text literal"""
    return s


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


def min_python(major, minor):
    return pytest.mark.skipif(
        sys.version_info[0:2] < (major, minor),
        reason=f"python < {major}.{minor}",
    )


def min_libcurl(major, minor, patch):
    return pytest.mark.skipif(
        pycurl_version_less_than(major, minor, patch),
        reason=f"libcurl < {major}.{minor}.{patch}",
    )


def removed_in_libcurl(major, minor, patch):
    return pytest.mark.skipif(
        not pycurl_version_less_than(major, minor, patch),
        reason=f"libcurl >= {major}.{minor}.{patch}",
    )


def skip_in_libcurl_versions(*versions):
    import pycurl

    c = pycurl.COMPILE_LIBCURL_VERSION_NUM
    version = (c >> 16 & 0xFF, c >> 8 & 0xFF, c & 0xFF)
    return pytest.mark.skipif(
        version in versions,
        reason=f"libcurl == {version[0]}.{version[1]}.{version[2]}",
    )


def skip_module_without_websockets():
    """Call at module level (via :func:`pytest.skip(allow_module_level=True)`)
    in WS test files. Requires both libcurl >= 7.86.0 AND the runtime
    library built with WebSocket support — distro libcurl often ships
    with ``--disable-websockets``."""
    import pycurl

    if pycurl_version_less_than(7, 86, 0) or "ws" not in pycurl.version_info()[8]:
        pytest.skip("libcurl built without WebSocket support", allow_module_level=True)


def only_ssl(fn):
    import pycurl

    # easier to check that pycurl supports https, although
    # theoretically it is not the same test.
    # pycurl.version_info()[8] is a tuple of protocols supported by libcurl
    return pytest.mark.skipif(
        "https" not in pycurl.version_info()[8],
        reason="libcurl does not support ssl",
    )(fn)


def only_telnet(fn):
    import pycurl

    # pycurl.version_info()[8] is a tuple of protocols supported by libcurl
    return pytest.mark.skipif(
        "telnet" not in pycurl.version_info()[8],
        reason="libcurl does not support telnet",
    )(fn)


def only_libssh2(fn):
    import pycurl

    return pytest.mark.skipif(
        "libssh2/" not in pycurl.version,
        reason="SSH backend is not libssh2",
    )(fn)


def only_ssl_backends(*backends):
    import pycurl

    # easier to check that pycurl supports https, although
    # theoretically it is not the same test.
    # pycurl.version_info()[8] is a tuple of protocols supported by libcurl
    if "https" not in pycurl.version_info()[8]:
        return pytest.mark.skipif(True, reason="libcurl does not support ssl")

    return pytest.mark.skipif(
        pycurl.COMPILE_SSL_LIB not in backends,
        reason=f"SSL backend is {pycurl.COMPILE_SSL_LIB}",
    )


def only_ssl_backends_with_min_libcurl(
    backend_versions: dict[str, tuple[int, int, int]],
):
    import pycurl

    if "https" not in pycurl.version_info()[8]:
        return pytest.mark.skipif(True, reason="libcurl does not support ssl")

    backend = pycurl.COMPILE_SSL_LIB
    if backend not in backend_versions:
        return pytest.mark.skipif(True, reason=f"SSL backend is {backend}")

    min_ver = backend_versions[backend]
    return pytest.mark.skipif(
        pycurl_version_less_than(*min_ver),
        reason=f"SSL backend {backend} requires libcurl >= "
        f"{min_ver[0]}.{min_ver[1]}.{min_ver[2]}",
    )


def only_ssl_ech(fn):
    import pycurl

    # easier to check that pycurl supports https, although
    # theoretically it is not the same test.
    # pycurl.version_info()[8] is a tuple of protocols supported by libcurl
    if "https" not in pycurl.version_info()[8]:
        return pytest.mark.skipif(True, reason="libcurl does not support ssl")(fn)

    # CURLOPT_ECH is experimental not yet supported by OpenSSL.
    supported = ["BoringSSL", "wolfSSL"]
    ssl_lib = pycurl.version_info()[5]
    return pytest.mark.skipif(
        not any(ssl_lib.startswith(lib) for lib in supported),
        reason=f"SSL runtime library is {ssl_lib}",
    )(fn)


def only_ipv6(fn):
    import pycurl

    return pytest.mark.skipif(
        not pycurl.version_info()[4] & pycurl.VERSION_IPV6,
        reason="libcurl does not support ipv6",
    )(fn)


def only_unix(fn):
    return pytest.mark.skipif(sys.platform == "win32", reason="Unix only")(fn)


def only_http2(fn):
    import pycurl

    return pytest.mark.skipif(
        not pycurl.version_info()[4] & pycurl.VERSION_HTTP2,
        reason="libcurl does not support HTTP version 2",
    )(fn)


def only_http3(fn):
    import pycurl

    return pytest.mark.skipif(
        not pycurl.version_info()[4] & pycurl.VERSION_HTTP3,
        reason="libcurl does not support HTTP version 3",
    )(fn)


def only_gssapi(fn):
    import pycurl

    return pytest.mark.skipif(
        not pycurl.version_info()[4] & pycurl.VERSION_GSSAPI,
        reason="libcurl does not support GSS-API",
    )(fn)


def only_tls_srp(fn):
    import pycurl

    return pytest.mark.skipif(
        not pycurl.version_info()[4] & pycurl.VERSION_TLSAUTH_SRP,
        reason="libcurl does not support TLS-SRP",
    )(fn)


def only_psl(fn):
    import pycurl

    return pytest.mark.skipif(
        not pycurl.version_info()[4] & pycurl.VERSION_PSL,
        reason="libcurl does not support libpsl",
    )(fn)


class guard_unknown_libcurl_option:
    """Context manager that turns an option-unavailable curl error into a
    skip. Wrap just the setopt/unsetopt call that exercises a libcurl
    feature depending on an external library, such as libssh2/gssapi,
    where libcurl does not provide a way of detecting whether the required
    libraries were compiled in. Any other curl error is a real failure and
    is re-raised.

    ``pycurl.error`` does not carry which option was being set, so pass
    its name (matching the ``pycurl``/``Curl`` attribute you used, e.g.
    ``util.guard_unknown_libcurl_option("SSH_KNOWNHOSTS")``) to get it into
    the skip message.

    Used as ``with util.guard_unknown_libcurl_option(...): ...`` rather
    than as a function decorator so that pytest reports the skip against
    the call site inside the test, not this context manager's own frame."""

    def __init__(self, option_name=None):
        self.option_name = option_name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        __tracebackhide__ = True

        if exc_type is None:
            return False

        import pycurl

        if exc_type is not pycurl.error:
            return False

        # CURLE_UNKNOWN_OPTION means libcurl does not know the option at
        # all, CURLE_NOT_BUILT_IN that it knows it but the backend lacks
        # support. Both constants exist only when built against libcurl
        # 7.21.5 or later.
        reasons = {
            getattr(pycurl, name, None): reason
            for name, reason in (
                ("E_UNKNOWN_OPTION", "unknown libcurl option"),
                ("E_NOT_BUILT_IN", "libcurl option not built-in"),
            )
        }
        reason = reasons.get(exc.args[0])
        if reason is not None:
            target = self.option_name if self.option_name is not None else exc
            pytest.skip(f"{reason}: {target}")

        return False


create_connection = socket.create_connection


def wait_for_network_service(netloc, check_interval, num_attempts):
    ok = False
    for i in range(num_attempts):
        try:
            conn = create_connection(netloc, check_interval)
        except socket.error:
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
    """This is a default curl with localhost -> 127.0.0.1 name mapping
    on windows systems, because they don't have it in the hosts file.
    """

    curl = DefaultCurl()

    if sys.platform == "win32":
        curl.setopt(curl.RESOLVE, ["localhost:%d:127.0.0.1" % port])

    return curl


def with_real_write_file(fn):
    @functools.wraps(fn)
    def wrapper(*args):
        with tempfile.NamedTemporaryFile() as f:
            return fn(*(list(args) + [f.file]))

    return wrapper


@contextlib.contextmanager
def redirected_fd(fd, replacement_path):
    """Temporarily point the OS-level file descriptor `fd` at
    `replacement_path`, restoring the original on exit. For redirecting
    C-level streams like `stdin`/`stdout` that native code (e.g. libcurl)
    reads/writes directly by fd, which plain sys.stdin/stdout swaps can't
    reach."""
    replacement_fd = os.open(replacement_path, os.O_RDONLY)
    saved_fd = os.dup(fd)
    try:
        os.dup2(replacement_fd, fd)
        yield
    finally:
        os.dup2(saved_fd, fd)
        os.close(saved_fd)
        os.close(replacement_fd)


def gc_collect_hard(rounds=3):
    for _ in range(rounds):
        gc.collect()


class LiveTracker:
    def __init__(self):
        self._items = []

    def track(self, name, obj):
        self._items.append((name, weakref.ref(obj), id(obj)))
        return obj

    def assert_all_gone(self):
        gc_collect_hard()
        live_ids = {id(o) for o in gc.get_objects()}
        for name, wref, obj_id in self._items:
            if wref() is None:
                continue
            tag = " (gc-tracked)" if obj_id in live_ids else ""
            raise AssertionError(f"{name} still alive{tag} (id={obj_id})")
