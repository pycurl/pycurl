import sys
import threading
import time
import curl


class Test(threading.Thread):

    def __init__(self, url, ofile):
        threading.Thread.__init__(self)
        self.curl = curl.init()
        self.curl.setopt(curl.URL, url)
        self.curl.setopt(curl.FILE, ofile)
        self.curl.setopt(curl.NOPROGRESS, 1)
        self.curl.setopt(curl.FOLLOWLOCATION, 1)
        self.curl.setopt(curl.MAXREDIRS, 5)

    def run(self):
        self.curl.perform()
        self.curl.cleanup()        
        sys.stdout.write('.')
        sys.stdout.flush()
        

# Read list of URIs from file specified on commandline
urls = open(sys.argv[1]).readlines()
threads = []
fileno = 0

# Start one thread per URI in parallel
t1 = time.time()
for url in urls:
    f = open(str(fileno), 'w')
    t = Test(url, f)
    t.start()
    threads.append((t, f))
    fileno = fileno + 1
# Wait for all threads to finish
for thread, file in threads:
    thread.join()
    file.close()
t2 = time.time()
print '\n** multithreading, %d seconds elapsed for %d uris' % (int(t2-t1), len(urls))

# Start on thread per URI in sequence
fileno = 0
t1 = time.time()
for url in urls:
    f = open(str(fileno), 'w')
    t = Test(url, f)
    t.start()
    fileno = fileno + 1
    t.join()
    f.close()
t2 = time.time()
print '\n** singlethreading, %d seconds elapsed for %d uris' % (int(t2-t1), len(urls))
