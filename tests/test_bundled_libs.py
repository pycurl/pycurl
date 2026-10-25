import os
import re

import pytest

import pycurl

# Distro packages often backport security fixes without changing the version
# number, so these checks only make sense for wheels that bundle the libraries
# vcpkg built. The wheel build sets PYCURL_TEST_BUNDLED_LIBS for its test step.
pytestmark = pytest.mark.skipif(
    not os.environ.get("PYCURL_TEST_BUNDLED_LIBS"),
    reason="only checked for wheels with bundled libraries",
)


def bundled_version(name):
    match = re.search(rf"\b{name}/(\d+)\.(\d+)\.(\d+)", pycurl.version)
    assert match, f"{name} not found in {pycurl.version!r}"
    return tuple(int(part) for part in match.groups())


def test_brotli_has_ghsa_9v8h_qqgm_4m35_fix():
    # Out-of-bounds write in the brotli decoder, fixed in 1.2.1.
    assert bundled_version("brotli") >= (1, 2, 1), pycurl.version
