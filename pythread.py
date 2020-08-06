import threading
import time

class PyThread(threading.Thread):

    def __init__(self, name='TestThread'):
        """ constructor, setting initial variables """
        self._stopevent = threading.Event()
        self._sleepperiod = 1.0

        threading.Thread.__init__(self, name=name)

    def run(self):
        """ main control loop """
        print("%s starts" % (self.getName(),))

        while not self._stopevent.isSet():
            self._stopevent.wait(self._sleepperiod)

        print("%s ends" % (self.getName(),))

    def join(self, timeout=None):
        """ Stop the thread. """
        self._stopevent.set()
        threading.Thread.join(self, timeout)
