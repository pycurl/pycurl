#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vi:ts=4:et

import sys, threading
import pycurl
import pygtk
pygtk.require('2.0')
import gtk

# We should ignore SIGPIPE when using pycurl.NOSIGNAL - see
# the libcurl tutorial for more info.
try:
    import signal
    from signal import SIGPIPE, SIG_IGN
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
except ImportError:
    pass


class ProgressBar:
    def __init__(self, uri):
        self.round = 0.0
        win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        win.set_title("PycURL progress")
        win.show()
        vbox = gtk.VBox(spacing=5)
        vbox.set_border_width(10)
        win.add(vbox)
        win.set_default_size(200, 20)
        vbox.show()
        label = gtk.Label("Downloading %s" % uri)
        label.set_alignment(0, 0.5)
        vbox.pack_start(label)
        label.show()
        pbar = gtk.ProgressBar()
        pbar.show()
        self.pbar = pbar
        vbox.pack_start(pbar)
        win.connect("destroy", self.close_app)

    def progress(self, download_t, download_d, upload_t, upload_d):
        if download_t == 0:
            self.round = self.round + 0.1
            if self.round >= 1.0:  self.round = 0.0
        else:
            self.round = float(download_d) / float(download_t)
        gtk.threads_enter()
        self.pbar.set_fraction(self.round)
        gtk.threads_leave()

    def mainloop(self):
        gtk.threads_enter()
        gtk.main()
        gtk.threads_leave()

    def close_app(self, *args):
        args[0].destroy()
        gtk.main_quit()


class Test(threading.Thread):
    def __init__(self, url, target_file, progress):
        threading.Thread.__init__(self)
        self.target_file = target_file
        self.progress = progress
        self.curl = pycurl.Curl()
        self.curl.setopt(pycurl.URL, url)
        self.curl.setopt(pycurl.WRITEDATA, self.target_file)
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.NOPROGRESS, 0)
        self.curl.setopt(pycurl.PROGRESSFUNCTION, self.progress)
        self.curl.setopt(pycurl.MAXREDIRS, 5)
        self.curl.setopt(pycurl.NOSIGNAL, 1)

    def run(self):
        self.curl.perform()
        self.curl.close()
        self.target_file.close()
        self.progress(1.0, 1.0, 0, 0)


# Check command line args
if len(sys.argv) < 3:
    print("Usage: %s <URL> <filename>" % sys.argv[0])
    raise SystemExit

# Make a progress bar window
p = ProgressBar(sys.argv[1])
# Start thread for fetching url
Test(sys.argv[1], open(sys.argv[2], 'wb'), p.progress).start()
# Enter the GTK mainloop
gtk.threads_init()
try:
    p.mainloop()
except KeyboardInterrupt:
    pass
