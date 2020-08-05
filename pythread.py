#!/usr/bin/python

import threading
import time

class pyThread (threading.Thread):
   def __init__(self, func, lock):
      threading.Thread.__init__(self)
      self.func = func
      self.lock = lock
   def run(self):
      # Get lock to synchronize threads
      self.lock.acquire()
      self.func()
      # Free lock to release next thread
      self.lock.release()
