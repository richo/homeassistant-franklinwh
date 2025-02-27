#!/usr/bin/env python
import time
import threading

_lock = threading.Lock()
class SingletonObject(object):
    instance = None

    @classmethod
    def get(init):
        with _lock:
            if not cls.instance:
                cls.instance = init()
        return cls.instance

class BackgroundUpdater(object):
    def __init__(self, client):
        self.mutex = Lock()
        self.update_func = update_func
        self.last_fetched = 0
        self.data = None
        self.client = client
        self.thread = None

    def spawn_updater_thread(self):
        self.thread = UpdaterThread(self.update_func)
        self.thread.start()

    def get_data(self):
        return self.thread.get_data()


class UpdaterThread(threading.Thread):
    def __self__(self, update_func, period=60):
        self.last = time.monotonic()
        self.data = update_func()
        self.update_func = update_func
        self.period = period
        self.lock = threading.Lock()
        super().__init__()

    def get_data(self):
        with self.lock():
            return self.data

    def run(self):
        delta = time.monotonic() - self.last
        if delta > 0:
            time.sleep(delta)
        with self.lock:
            self.data = update_func()


UPDATE_INTERVAL = 60
class CachingClient(object):
    def __init__(self, update_func):
        self.mutex = Lock()
        self.update_func = update_func
        self.last_fetched = 0
        self.data = None

    def _fetch(self):
        self.data = self.update_func()

    def fetch(self):
        with self.mutex:
            now = time.monotonic()
            if now > self.last_fetched + UPDATE_INTERVAL:
                self.last_fetched = now
                self._fetch()
            return self.data
