# $Id$

## System modules
import sys, threading
from gtk import *

## PycURL module
import pycurl


def progress(download_t, download_d, upload_t, upload_d):
    threads_enter()
    global round, pbar
    if download_t == 0:
        round = round + 0.1
        if round >= 1.0:  round = 0.0
    else:
        round = float(download_d) / float(download_t)
    pbar.update(round)
    threads_leave()
    return 0 # Anything else indicates an error


def close_app(*args):
    args[0].destroy()
    mainquit()
    return TRUE


class Test(threading.Thread):

    def __init__(self, url, target_file):
        threading.Thread.__init__(self)
        self.target_file = target_file
        self.curl = pycurl.init()
        self.curl.setopt(pycurl.URL, url)
        self.curl.setopt(pycurl.FILE, target_file)
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.NOPROGRESS, 0)
        self.curl.setopt(pycurl.PROGRESSFUNCTION, progress)
        self.curl.setopt(pycurl.MAXREDIRS, 5)

    def run(self):
        self.curl.perform()
        self.curl.cleanup()        
        self.target_file.close()
        progress(1.0, 1.0, 0, 0)
        

# Check command line args
if len(sys.argv) < 3:
    print "Usage: %s <URL> <filename>" % sys.argv[0]
    raise SystemExit

# Launch a window with a statusbar
win = GtkDialog()
win.set_title("PycURL progress")
win.show()
vbox = GtkVBox(spacing=5)
vbox.set_border_width(10)
win.vbox.pack_start(vbox)
win.set_default_size(200, 20)
vbox.show()
label = GtkLabel("Downloading %s" % sys.argv[1])
label.set_alignment(0, 0.5)
vbox.pack_start(label, expand=FALSE)
label.show()
pbar = GtkProgressBar()
pbar.show()
vbox.pack_start(pbar)
win.connect("destroy", close_app)
win.connect("delete_event", close_app)

# Start thread for fetching url
round = 0.0
Test(sys.argv[1], open(sys.argv[2], 'w')).start()

# Start GTK mainloop
threads_enter()
mainloop()
threads_leave()
