#!/usr/bin/python

import sys
import pycurl

saw_error = 1

def main():
        global saw_error

        pycurl.global_init(pycurl.GLOBAL_DEFAULT)

        outf = file("/dev/null", "rb+")
        cm = pycurl.CurlMulti()

        # Set multi handle's options
        cm.setopt(pycurl.M_PIPELINING, 1)

        eh = pycurl.Curl()

        for x in range(1, 20):

                eh.setopt(pycurl.WRITEDATA, outf)
                eh.setopt(pycurl.URL, sys.argv[1])
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
                        print "Transfer to %s failed with %d, %s\n" % \
                            (h.getinfo(pycurl.EFFECTIVE_URL), en, em)
                        raise RuntimeError

                for h in good:
                        httpcode = h.getinfo(pycurl.RESPONSE_CODE)
                        if httpcode != 200:
                                print "Transfer to %s failed with code %d\n" %\
                                    (h.getinfo(pycurl.EFFECTIVE_URL), httpcode)
                                raise RuntimeError

                        else:
                                print "Recd %d bytes from %s" % \
                                    (h.getinfo(pycurl.SIZE_DOWNLOAD),
                                    h.getinfo(pycurl.EFFECTIVE_URL))

                cm.remove_handle(eh)
                eh.reset()

        eh.close()
        cm.close()
        outf.close()

        pycurl.global_cleanup()


if __name__ == '__main__':
        if len(sys.argv) != 2:
                print "Usage: %s <url>" % sys.argv[0]
                sys.exit(2)
        main()

