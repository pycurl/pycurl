# $Id$
# vi:ts=4:et

import sys, threading, Queue
import pycurl


class WorkerThread(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue

    def run(self):
        while 1:
            try:
                url, filename = self.queue.get_nowait()
            except Queue.Empty:
                break
            f = open(filename, "wb")
            curl = pycurl.Curl()
            curl.setopt(pycurl.FOLLOWLOCATION, 1)
            curl.setopt(pycurl.MAXREDIRS, 5)
            curl.setopt(pycurl.URL, url)
            curl.setopt(pycurl.WRITEDATA, f)
            try:
                curl.perform()
            except:
                pass
            curl.close()
            f.close()
            sys.stdout.write(".")
            sys.stdout.flush()

# Read list of URLs from file specified on commandline
try:
    urls = open(sys.argv[1]).readlines()
    num_workers = int(sys.argv[2])
except:
    # File or number of workers was not specified, show usage string
    print "Usage: %s <file with URLs to fetch> <number of workers>" % sys.argv[0]
    raise SystemExit

# Initialize thread array and the file number used to store documents
threads = []
fileno = 0
queue = Queue.Queue()

# Fill the work input queue with URLs
for url in urls:
    fileno = fileno + 1
    filename = "data_%d" % (fileno,)
    queue.put((url, filename))

# Start a bunch of threads
for num_threads in range(num_workers):
    t = WorkerThread(queue)
    t.start()
    threads.append(t)

# Wait for all threads to finish
for thread in threads:
    thread.join()
