import logging
from threading import (
    Event,
    Thread,
)

from galaxy.util import ExecutionTimer

log = logging.getLogger(__name__)


class IntervalTask:
    def __init__(self, func, name="Periodic task", interval=3600, immediate_start=False, time_execution=False):
        """
        Run an arbitrary function `func` every `interval` seconds.

        Set `immediate_start` to True to run `func` when task is started.
        """
        self.func = func
        self.name = name
        self.interval = interval
        self.time_execution = time_execution
        self.immediate_start = immediate_start
        self.event = Event()
        self.thread = Thread(target=self.run, name=self.name, daemon=True)
        self.running = False

    def start(self):
        self.running = True
        self.thread.start()

    def _exec(self):
        if self.time_execution:
            timer = ExecutionTimer()
        self.func()
        if self.time_execution:
            log.debug(f"Executed periodic task {self.name} {timer}")

    def run(self):
        if self.immediate_start:
            self._exec()
        while not self.event.is_set():
            self.event.wait(self.interval)
            if self.running:
                self._exec()

    def shutdown(self):
        self.running = False
        self.event.set()
        self.thread.join(5)
