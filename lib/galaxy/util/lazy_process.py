import subprocess
import threading
import time


class LazyProcess:
    """ Abstraction describing a command line launching a service - probably
    as needed as functionality is accessed in Galaxy.
    """

    def __init__(self, command_and_args):
        self.command_and_args = command_and_args
        self.thread_lock = threading.Lock()
        self.allow_process_request = True
        self.process = None

    def start_process(self):
        with self.thread_lock:
            if self.allow_process_request:
                self.allow_process_request = False
                t = threading.Thread(target=self.__start)
                t.daemon = True
                t.start()

    def __start(self):
        with self.thread_lock:
            self.process = subprocess.Popen(self.command_and_args, close_fds=True)

    def shutdown(self):
        with self.thread_lock:
            self.allow_process_request = False
        if self.running:
            self.process.terminate()
            time.sleep(.01)
            if self.running:
                self.process.kill()

    @property
    def running(self):
        return self.process and not self.process.poll()


class NoOpLazyProcess:
    """ LazyProcess abstraction meant to describe potentially optional
    services, in those cases where one is not configured or valid, this
    class can be used in place of LazyProcess.
    """

    def start_process(self):
        return

    def shutdown(self):
        return

    @property
    def running(self):
        return False
