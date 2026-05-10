import pytest
import pycurl

from . import util

pytestmark = pytest.mark.ssh


@util.min_libcurl(7, 19, 6)
@util.guard_unknown_libcurl_option
def test_keyfunction_fine(sftp_curl, known_hosts_file):
    sftp_curl.setopt(pycurl.SSH_KNOWNHOSTS, known_hosts_file)
    sftp_curl.setopt(pycurl.SSH_KEYFUNCTION, lambda known_key, found_key, match: pycurl.KHSTAT_FINE)

    with pytest.raises(pycurl.error) as exc_info:
        sftp_curl.perform()
    assert exc_info.value.args[0] == pycurl.E_LOGIN_DENIED


@util.min_libcurl(7, 19, 6)
@util.guard_unknown_libcurl_option
def test_keyfunction_reject(sftp_curl, known_hosts_file):
    sftp_curl.setopt(pycurl.SSH_KNOWNHOSTS, known_hosts_file)
    sftp_curl.setopt(pycurl.SSH_KEYFUNCTION, lambda known_key, found_key, match: pycurl.KHSTAT_REJECT)

    with pytest.raises(pycurl.error) as exc_info:
        sftp_curl.perform()
    assert exc_info.value.args[0] == pycurl.E_PEER_FAILED_VERIFICATION


@util.min_libcurl(7, 19, 6)
@util.guard_unknown_libcurl_option
def test_keyfunction_bogus_return(sftp_curl, known_hosts_file):
    sftp_curl.setopt(pycurl.SSH_KNOWNHOSTS, known_hosts_file)
    sftp_curl.setopt(pycurl.SSH_KEYFUNCTION, lambda known_key, found_key, match: 'bogus')

    with pytest.raises(pycurl.error) as exc_info:
        sftp_curl.perform()
    assert exc_info.value.args[0] == pycurl.E_PEER_FAILED_VERIFICATION


@util.min_libcurl(7, 19, 6)
@util.guard_unknown_libcurl_option
def test_keyfunction_set_none(sftp_curl):
    sftp_curl.setopt(pycurl.SSH_KEYFUNCTION, None)


@util.min_libcurl(7, 19, 6)
@util.guard_unknown_libcurl_option
def test_keyfunction_unset(sftp_curl):
    sftp_curl.unsetopt(pycurl.SSH_KEYFUNCTION)
