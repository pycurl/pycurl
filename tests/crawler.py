# $Id$

## System modules
import sys
import threading
import Queue

## PycURL module
import pycurl


class WorkerThread(threading.Thread):

    def __init__(self, iq):
        threading.Thread.__init__(self)
        self.iq = iq
        self.curl = pycurl.init()
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.MAXREDIRS, 5)

    def run(self):
        while 1:
            try:
                url, no = self.iq.get_nowait()
            except:
                self.curl.cleanup()
                break
            f = open(str(no), 'w')
            self.curl.setopt(pycurl.URL, url)
            self.curl.setopt(pycurl.WRITEDATA, f)
            self.curl.perform()
            sys.stdout.write('.')
            sys.stdout.flush()

# Read list of URIs from file specified on commandline
try:
    urls = open(sys.argv[1]).readlines()
except IndexError:
    # No file was specified, show usage string
    print "Usage: %s <file with uris to fetch>" % sys.argv[0]
    raise SystemExit

# Initialize thread array and the file number
threads = []
fileno = 0
iq = Queue.Queue()

# Fill the work queue with uris
for url in urls:
    fileno = fileno + 1
    iq.put((url, fileno))

# Start a bunch of threads
for num_threads in range(32):
    t = WorkerThread(iq)
    t.start()
    threads.append(t)

# Wait for all threads to finish
for thread in threads:
    thread.join()
