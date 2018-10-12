from __future__ import absolute_import

import logging
import threading

from galaxy.web.stack import register_postfork_function
from .sleeper import Sleeper

log = logging.getLogger(__name__)

DEFAULT_MONITOR_THREAD_JOIN_TIMEOUT = 5


class Monitors(object):

    def _init_monitor_thread(self, name, target_name=None, target=None, start=False, config=None):
        self.monitor_join_sleep = getattr(config, "monitor_thread_join_timeout", DEFAULT_MONITOR_THREAD_JOIN_TIMEOUT)
        self.monitor_join = self.monitor_join_sleep > 0
        self.monitor_sleeper = Sleeper()
        self.monitor_running = True

        if target is not None:
            assert target_name is None
            monitor_func = target
        else:
            target_name = target_name or "monitor"
            monitor_func = getattr(self, target_name)
        self.sleeper = Sleeper()
        self.monitor_thread = threading.Thread(name=name, target=monitor_func)
        self.monitor_thread.setDaemon(True)
        self._start = start
        register_postfork_function(self.start_monitoring)

    def start_monitoring(self):
        if self._start:
            self.monitor_thread.start()

    def stop_monitoring(self):
        self.monitor_running = False

    def _monitor_sleep(self, sleep_amount):
        self.sleeper.sleep(sleep_amount)

    def shutdown_monitor(self):
        self.stop_monitoring()
        self.sleeper.wake()
        if self.monitor_join:
            log.debug("Joining monitor thread")
            self.monitor_thread.join(self.monitor_join_sleep)
