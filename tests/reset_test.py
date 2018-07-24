#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

from . import localhost
import pycurl
import unittest

from . import appmanager
from . import util

setup_module, teardown_module = appmanager.setup(('app', 8380))

class ResetTest(unittest.TestCase):
    def test_reset(self):
        c = util.DefaultCurl()
        c.setopt(pycurl.USERAGENT, 'Phony/42')
        c.setopt(pycurl.URL, 'http://%s:8380/header?h=user-agent' % localhost)
        sio = util.BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, sio.write)
        c.perform()
        user_agent = sio.getvalue().decode()
        assert user_agent == 'Phony/42'

        c.reset()
        c.setopt(pycurl.URL, 'http://%s:8380/header?h=user-agent' % localhost)
        sio = util.BytesIO()
        c.setopt(pycurl.WRITEFUNCTION, sio.write)
        c.perform()
        user_agent = sio.getvalue().decode()
        # we also check that the request succeeded after curl
        # object has been reset
        assert user_agent.startswith('PycURL')

    # XXX this test was broken when it was test_reset.py
    def skip_reset_with_multi(self):
        outf = util.BytesIO()
        cm = pycurl.CurlMulti()

        eh = util.DefaultCurl()

        for x in range(1, 20):
            eh.setopt(pycurl.WRITEFUNCTION, outf.write)
            eh.setopt(pycurl.URL, 'http://%s:8380/success' % localhost)
            cm.add_handle(eh)

            while 1:
                ret, active_handles = cm.perform()
                if ret != pycurl.E_CALL_MULTI_PERFORM:
                    break

            while active_handles:
                ret = cm.select(1.0)
                if ret == -1:
                    continue
                while 1:
                    ret, active_handles = cm.perform()
                    if ret != pycurl.E_CALL_MULTI_PERFORM:
                        break

            count, good, bad = cm.info_read()

            for h, en, em in bad:
                print("Transfer to %s failed with %d, %s\n" % \
                    (h.getinfo(pycurl.EFFECTIVE_URL), en, em))
                raise RuntimeError

            for h in good:
                httpcode = h.getinfo(pycurl.RESPONSE_CODE)
                if httpcode != 200:
                    print("Transfer to %s failed with code %d\n" %\
                        (h.getinfo(pycurl.EFFECTIVE_URL), httpcode))
                    raise RuntimeError

                else:
                    print("Recd %d bytes from %s" % \
                        (h.getinfo(pycurl.SIZE_DOWNLOAD),
                        h.getinfo(pycurl.EFFECTIVE_URL)))

            cm.remove_handle(eh)
            eh.reset()

        eh.close()
        cm.close()
        outf.close()
