#! /usr/bin/env python
# vi:ts=4:et
# $Id$

import sys, os, urllib, cStringIO, threading, Queue, time
from gtk import *
from gnome.ui import *
from gtkhtml import *
import pycurl

# We should ignore SIGPIPE when using pycurl.NOSIGNAL - see the libcurl
# documentation `libcurl-the-guide' for more info.
import signal
signal.signal(signal.SIGPIPE, signal.SIG_IGN)


# URL history
history = []
# Links for 'forward'
forward = []
# Number of concurrent connections to the web-server
NUM_THREADS = 4

# About
def about(button):
    GnomeAbout('GtkHTML Test with PycURL', '',
                'License GPL2',
                ['Original code by Matt Wilson, modified by Kjetil Jacobsen'],
                ('This is a useless application demonstrating the '
                'GtkHTML widget with Python and PycURL.')).show()

# HTML template for reporting internal errors
internal_error = """
<html>
<head>
<title>Error</title>
</head>
<body>
<h1>Error</h1>
<b>%s</b>
</body>
</html>
"""


# Worker threads downloads objects and passes them to the renderer
class WorkerThread(threading.Thread):

    def __init__(self, queue, render):
        threading.Thread.__init__(self)
        self.queue = queue      # Download request queue
        self.render = render    # Render output queue

    def run(self):
        curl = pycurl.Curl()
        curl.setopt(pycurl.FOLLOWLOCATION, 1)
        curl.setopt(pycurl.MAXREDIRS, 5)
        curl.setopt(pycurl.NOSIGNAL, 1)
        curl.setopt(pycurl.HTTPHEADER, ["User-Agent: GtkHTML/PycURL demo browser"])
        while 1:
            url, handle = self.queue.get()
            if url == None:
                curl.close()
                raise SystemExit
            b = cStringIO.StringIO()
            curl.setopt(pycurl.WRITEFUNCTION, b.write)
            curl.setopt(pycurl.URL, url)
            try:
                curl.perform()
            except pycurl.error, msg:
                b.write(internal_error % msg[1])
            except:
                msg = "Error retrieving URL: %s" % url
                b.write(internal_error % msg)
            # Flag empty documents to the renderer
            if b.tell() == 0:
                b.close()
                b = None
            # Enqueue the document on the rendering pipeline
            self.render.append((b, handle))


# Main rendering window, handles gtk events and sends requests to worker threads
class HtmlWindow(GtkHTML):

    def __init__(self):
        GtkHTML.__init__(self)
        self.queue = Queue.Queue()
        self.render = []
        self.threads = []
        for num_threads in range(NUM_THREADS):
            t = WorkerThread(self.queue, self.render)
            t.start()
            self.threads.append(t)

    def mainquit(self, *args):
        # Send a 'terminate' message to the worker threads
        for t in self.threads:
            t.queue.put((None, None))
        mainquit()

    def load_url(self, html, url):
        t1 = time.time()
        self.num_obj = 0
        if history: url = urllib.basejoin(history[-1], url)
        history.append(url)
        html.load_empty()
        handle = html.begin()
        url = url.strip()
        self.request_url(html, url, handle)
        self.urlentry.set_text(url)
        # Render incoming objects
        while self.num_obj > 0:
            if len(self.render) == 0:
                mainiteration(0)
                continue
            self.num_obj -= 1
            buf, handle = self.render.pop(0)
            if buf != None:
                html.write(handle, buf.getvalue())
                buf.close()
            html.end(handle, HTML_STREAM_OK)
        # Finished rendering page
        t2 = time.time()
        self.statusbar.set_text("Done (%.3f seconds)" % (t2-t1))

    def submit(self, html, method, path, params):
        if method != 'GET':
            print "Submit currently only works for GET requests, not POST"
            return
        if params != None: path += "?" + params
        url = urllib.basejoin(history[-1], path)
        self.load_url(html, url)

    def request_url(self, html, url, handle):
        url = urllib.basejoin(history[-1], url)
        self.statusbar.set_text("Requesting URL: %s" % url)
        self.queue.put((url, handle))
        self.num_obj += 1

    def entry_activate(self, entry, html):
        url = entry.get_text()
        self.load_url(html, url)
        del forward[:]

    def do_back(self, _b):
        if len(history) > 1:
            forward.append(history[-1])
            del history[-1]
            url = history[-1]
            del history[-1]
            self.load_url(html, url)

    def do_forward(self, _b):
        if len(forward) == 0: return
        self.load_url(html, forward[-1])
        del forward[-1]

    def do_reload(self, _b):
        if len(history) == 0: return
        url = history[-1]
        del history[-1]
        self.load_url(html, url)



# Setup windows and menus
html = HtmlWindow()

file_menu = [
    UIINFO_ITEM_STOCK('Quit', None, html.mainquit, STOCK_MENU_QUIT),
]
help_menu = [
    UIINFO_ITEM_STOCK('About...', None, about, STOCK_MENU_ABOUT),
]
menus = [
    UIINFO_SUBTREE('File', file_menu),
    UIINFO_SUBTREE('Help', help_menu)
]

toolbar = [
    UIINFO_ITEM_STOCK('Back', 'Previous page', html.do_back, STOCK_MENU_BACK),
    UIINFO_ITEM_STOCK('Forward', 'Next page', html.do_forward, STOCK_MENU_FORWARD),
    UIINFO_ITEM_STOCK('Reload', 'Reload current page', html.do_reload, STOCK_MENU_REFRESH)
]

win = GnomeApp("html_demo", "Python GtkHTML Test")
win.set_wmclass("gtk_html_test", "GtkHTMLTest")
win.connect('delete_event', html.mainquit)

vbox = GtkVBox(spacing=3)
vbox.set_border_width(2)
vbox.show()
win.set_contents(vbox)

entry = GtkEntry()
html.connect('url_requested', html.request_url)
html.connect('link_clicked', html.load_url)
html.connect('submit', html.submit)
entry.connect('activate', html.entry_activate, html)
vbox.pack_start(entry, expand=FALSE)
entry.show()
html.urlentry = entry
html.set_usize(800, 600)

sw = GtkScrolledWindow()
sw.set_policy(POLICY_AUTOMATIC, POLICY_AUTOMATIC)
sw.add(html)
vbox.pack_start(sw)

sep = GtkHSeparator()
vbox.pack_start(sep, expand=FALSE)

status = GtkLabel('')
status.set_justify(JUSTIFY_LEFT)
status.set_alignment(0.0, 0.5)
win.set_statusbar(status)
win.create_menus(menus)
win.create_toolbar(toolbar)

html.statusbar = status
html.load_empty()

win.show_all()

threads_enter()
mainloop()
threads_leave()
