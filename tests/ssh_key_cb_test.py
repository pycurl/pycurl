import base64
import hashlib
from collections.abc import Callable

import pytest
import pycurl

from . import util

pytestmark = pytest.mark.ssh


def sha256_fingerprint(key_blob: bytes) -> str:
    return base64.b64encode(hashlib.sha256(key_blob).digest()).decode()


def recording_hostkeyfunction(
    result: object,
) -> tuple[Callable[[int, bytes], object], list[tuple[int, bytes]]]:
    calls: list[tuple[int, bytes]] = []

    def hostkeyfunction(keytype: int, key: bytes) -> object:
        calls.append((keytype, key))
        return result

    return hostkeyfunction, calls


@util.min_libcurl(7, 19, 6)
def test_keyfunction_fine(sftp_curl, known_hosts_file):
    with util.guard_unknown_libcurl_option("SSH_KNOWNHOSTS"):
        sftp_curl.setopt(pycurl.SSH_KNOWNHOSTS, known_hosts_file)
    with util.guard_unknown_libcurl_option("SSH_KEYFUNCTION"):
        sftp_curl.setopt(pycurl.SSH_KEYFUNCTION, lambda known_key, found_key, match: pycurl.KHSTAT_FINE)

    with pytest.raises(pycurl.error) as exc_info:
        sftp_curl.perform()
    assert exc_info.value.args[0] == pycurl.E_LOGIN_DENIED


@util.min_libcurl(7, 19, 6)
def test_keyfunction_reject(sftp_curl, known_hosts_file):
    with util.guard_unknown_libcurl_option("SSH_KNOWNHOSTS"):
        sftp_curl.setopt(pycurl.SSH_KNOWNHOSTS, known_hosts_file)
    with util.guard_unknown_libcurl_option("SSH_KEYFUNCTION"):
        sftp_curl.setopt(pycurl.SSH_KEYFUNCTION, lambda known_key, found_key, match: pycurl.KHSTAT_REJECT)

    with pytest.raises(pycurl.error) as exc_info:
        sftp_curl.perform()
    assert exc_info.value.args[0] == pycurl.E_PEER_FAILED_VERIFICATION


@util.min_libcurl(7, 19, 6)
def test_keyfunction_bogus_return(sftp_curl, known_hosts_file):
    with util.guard_unknown_libcurl_option("SSH_KNOWNHOSTS"):
        sftp_curl.setopt(pycurl.SSH_KNOWNHOSTS, known_hosts_file)
    with util.guard_unknown_libcurl_option("SSH_KEYFUNCTION"):
        sftp_curl.setopt(pycurl.SSH_KEYFUNCTION, lambda known_key, found_key, match: 'bogus')

    with pytest.raises(pycurl.error) as exc_info:
        sftp_curl.perform()
    assert exc_info.value.args[0] == pycurl.E_PEER_FAILED_VERIFICATION


@util.min_libcurl(7, 19, 6)
def test_keyfunction_set_none(sftp_curl):
    with util.guard_unknown_libcurl_option("SSH_KEYFUNCTION"):
        sftp_curl.setopt(pycurl.SSH_KEYFUNCTION, None)


@util.min_libcurl(7, 19, 6)
def test_keyfunction_unset(sftp_curl):
    with util.guard_unknown_libcurl_option("SSH_KEYFUNCTION"):
        sftp_curl.unsetopt(pycurl.SSH_KEYFUNCTION)


@util.min_libcurl(7, 80, 0)
@util.only_libssh2
@pytest.mark.parametrize(
    "make_fingerprint, expected_error",
    [
        (sha256_fingerprint, pycurl.E_LOGIN_DENIED),
        (lambda blob: sha256_fingerprint(blob).rstrip("="), pycurl.E_LOGIN_DENIED),
        (
            lambda blob: sha256_fingerprint(b"another host key"),
            pycurl.E_PEER_FAILED_VERIFICATION,
        ),
    ],
    ids=["match", "match-unpadded", "mismatch"],
)
def test_host_public_key_sha256(
    sftp_curl, sftp_server, make_fingerprint, expected_error
):
    fingerprint = make_fingerprint(sftp_server.host_key.asbytes())
    with util.guard_unknown_libcurl_option("SSH_HOST_PUBLIC_KEY_SHA256"):
        sftp_curl.setopt(pycurl.SSH_HOST_PUBLIC_KEY_SHA256, fingerprint)

    with pytest.raises(pycurl.error) as exc_info:
        sftp_curl.perform()
    assert exc_info.value.args[0] == expected_error


@util.min_libcurl(7, 84, 0)
@util.only_libssh2
@pytest.mark.parametrize(
    "result, expected_error",
    [
        (pycurl.KHMATCH_OK, pycurl.E_LOGIN_DENIED),
        (pycurl.KHMATCH_MISMATCH, pycurl.E_PEER_FAILED_VERIFICATION),
        ("bogus", pycurl.E_PEER_FAILED_VERIFICATION),
    ],
    ids=["accept", "reject", "bogus-return"],
)
def test_hostkeyfunction(sftp_curl, sftp_server, result, expected_error):
    hostkeyfunction, calls = recording_hostkeyfunction(result)
    with util.guard_unknown_libcurl_option("SSH_HOSTKEYFUNCTION"):
        sftp_curl.setopt(pycurl.SSH_HOSTKEYFUNCTION, hostkeyfunction)

    with pytest.raises(pycurl.error) as exc_info:
        sftp_curl.perform()
    assert exc_info.value.args[0] == expected_error
    assert calls == [(pycurl.KHTYPE_RSA, sftp_server.host_key.asbytes())]


@util.min_libcurl(7, 84, 0)
@util.only_libssh2
def test_hostkeyfunction_exception(sftp_curl):
    def hostkeyfunction(keytype, key):
        raise ValueError

    with util.guard_unknown_libcurl_option("SSH_HOSTKEYFUNCTION"):
        sftp_curl.setopt(pycurl.SSH_HOSTKEYFUNCTION, hostkeyfunction)

    with pytest.raises(ValueError):
        sftp_curl.perform()


@util.min_libcurl(7, 84, 0)
@util.only_libssh2
@pytest.mark.parametrize("clear", [True, False], ids=["set-none", "unsetopt"])
def test_hostkeyfunction_cleared(sftp_curl, clear):
    hostkeyfunction, calls = recording_hostkeyfunction(pycurl.KHMATCH_MISMATCH)
    with util.guard_unknown_libcurl_option("SSH_HOSTKEYFUNCTION"):
        sftp_curl.setopt(pycurl.SSH_HOSTKEYFUNCTION, hostkeyfunction)
    if clear:
        sftp_curl.setopt(pycurl.SSH_HOSTKEYFUNCTION, None)
    else:
        sftp_curl.unsetopt(pycurl.SSH_HOSTKEYFUNCTION)

    with pytest.raises(pycurl.error) as exc_info:
        sftp_curl.perform()
    assert exc_info.value.args[0] == pycurl.E_LOGIN_DENIED
    assert calls == []


@util.min_libcurl(7, 84, 0)
@util.only_libssh2
def test_hostkeyfunction_duphandle(sftp_curl, sftp_server):
    hostkeyfunction, calls = recording_hostkeyfunction(pycurl.KHMATCH_OK)
    with util.guard_unknown_libcurl_option("SSH_HOSTKEYFUNCTION"):
        sftp_curl.setopt(pycurl.SSH_HOSTKEYFUNCTION, hostkeyfunction)

    dup = sftp_curl.duphandle()
    try:
        with pytest.raises(pycurl.error) as exc_info:
            dup.perform()
    finally:
        dup.close()
    assert exc_info.value.args[0] == pycurl.E_LOGIN_DENIED
    assert calls == [(pycurl.KHTYPE_RSA, sftp_server.host_key.asbytes())]
