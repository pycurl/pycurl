# $Id$

## System modules
import sys, threading

## GNOME/Gtk modules
from gtk import *
from gnome.ui import *

## PycURL module
import pycurl


def progress(download_t, download_d, upload_t, upload_d):
    global round, appbar
    if download_t == 0:
        appbar.get_progress().set_activity_mode(1)
        round = round + 0.1
    else:
        appbar.get_progress().set_activity_mode(0)
        round = float(download_d) / float(download_t)
    appbar.set_progress(round)
    return 0 # Anything else indicates an error


class Test(threading.Thread):

    def __init__(self, url):
        threading.Thread.__init__(self)
        self.curl = pycurl.init()
        self.curl.setopt(pycurl.URL, url)
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.NOPROGRESS, 0)
        self.curl.setopt(pycurl.PROGRESSFUNCTION, progress)
        self.curl.setopt(pycurl.MAXREDIRS, 5)

    def run(self):
        self.curl.perform()
        self.curl.cleanup()        


win = GnomeApp('test', 'test')
appbar = GnomeAppBar()
appbar.show()
appbar.set_status('Download status')
win.set_statusbar(appbar)
win.show()

round = 0.0
t = Test(sys.argv[1])
t.start()

threads_enter()
mainloop()
threads_leave()
