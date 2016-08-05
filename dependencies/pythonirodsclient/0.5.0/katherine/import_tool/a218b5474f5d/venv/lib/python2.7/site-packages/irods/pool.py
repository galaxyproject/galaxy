import logging
import threading

from irods.connection import Connection

logger = logging.getLogger(__name__)

class Pool(object):
    def __init__(self, account):
        self.account = account
        self._lock = threading.Lock()
        self.active = set()
        self.idle = set()
        
    def get_connection(self):
        with self._lock:
            try:
                conn = self.idle.pop()
            except KeyError:
                conn = Connection(self, self.account)
            self.active.add(conn)
        logger.debug('num active: %d' % len(self.active))
        return conn

    def release_connection(self, conn, destroy=False):
        with self._lock:
            if conn in self.active:
                self.active.remove(conn)
                if not destroy:
                    self.idle.add(conn)
            elif conn in self.idle and destroy:
                self.idle.remove(conn)
        logger.debug('num idle: %d' % len(self.idle))
