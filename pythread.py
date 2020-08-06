#!/usr/bin/python

import threading
import time


class PyThread(threading.Thread):

    def _ _init_ _(self, func, args, name='TestThread', sleepperiod=1.0):
        """ constructor, setting initial variables """
        self._stopevent = threading.Event(  )
        self._sleepperiod = sleepperiod
        self.func = func
        self.args = args

        threading.Thread._ _init_ _(self, name=name)

    def run(self):
        """ main control loop """
        print "%s starts" % (self.getName(  ),)

        while not self._stopevent.isSet(  ):
            self.func(args)
            self._stopevent.wait(self._sleepperiod)

        print "%s ends" % (self.getName(  ),)

    def join(self, timeout=None):
        """ Stop the thread. """
        self._stopevent.set(  )
        threading.Thread.join(self, timeout)
