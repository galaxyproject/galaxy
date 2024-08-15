"""Web application stack operations
"""

import logging
import threading

log = logging.getLogger(__name__)


class ApplicationStackTransport:
    SHUTDOWN_MSG = "__SHUTDOWN__"

    def __init__(self, app, stack, dispatcher=None):
        """Pre-fork initialization."""
        self.app = app
        self.stack = stack
        self.can_run = False
        self.running = False
        self.dispatcher = dispatcher
        self.dispatcher_thread = None

    def init_late_prefork(self):
        pass

    def _dispatch_messages(self):
        pass

    def start_if_needed(self):
        # Don't unnecessarily start a thread that we don't need.
        if (
            self.can_run
            and not self.running
            and not self.dispatcher_thread
            and self.dispatcher
            and self.dispatcher.handler_count
        ):
            self.running = True
            self.dispatcher_thread = threading.Thread(
                name=f"{self.__class__.__name__}.dispatcher_thread", target=self._dispatch_messages
            )
            self.dispatcher_thread.start()
            log.info("%s dispatcher started", self.__class__.__name__)

    def stop_if_unneeded(self):
        if (
            self.can_run
            and self.running
            and self.dispatcher_thread
            and self.dispatcher
            and not self.dispatcher.handler_count
        ):
            self.running = False
            self.dispatcher_thread.join()
            self.dispatcher_thread = None
            log.info("%s dispatcher stopped", self.__class__.__name__)

    def start(self):
        """Post-fork initialization."""
        self.can_run = True
        self.start_if_needed()

    def send_message(self, msg, dest):
        pass

    def shutdown(self):
        self.running = False
        if self.dispatcher_thread:
            log.info("Joining application stack transport dispatcher thread")
            self.dispatcher_thread.join()
            self.dispatcher_thread = None
