# $Id$

## System modules
import sys, threading

## Gtk modules
from gtk import *

## PycURL module
import pycurl


def progress(download_t, download_d, upload_t, upload_d):
    global round, pbar
    if download_t == 0:
        pbar.set_activity_mode(1)
        round = round + 0.1
    else:
        pbar.set_activity_mode(0)
        round = float(download_d) / float(download_t)
    pbar.update(round)
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

# Read list of URIs from file specified on commandline
if len(sys.argv) < 2:
    # No uri was specified, show usage string
    print "Usage: %s <URI>" % sys.argv[0]
    raise SystemExit

# Launch a window with a statusbar
win = GtkDialog()
win.set_title("PycURL progress")
win.show()
vbox = GtkVBox(spacing=5)
vbox.set_border_width(10)
win.vbox.pack_start(vbox)
vbox.show()
label = GtkLabel("Download progress")
label.set_alignment(0, 0.5)
vbox.pack_start(label, expand=FALSE)
label.show()
pbar = GtkProgressBar()
pbar.set_usize(200, 20)
vbox.pack_start(pbar)
pbar.show()

# Start thread for fetching url
round = 0.0
t = Test(sys.argv[1])
t.start()

# Start GTK mainloop
threads_enter()
mainloop()
threads_leave()
