import subprocess
import threading


class LazyProcess:
    """Abstraction describing a command line launching a service - probably
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

    def shutdown(self, timeout: float = 5):
        """Terminate the process and reap it; kill it if it outlives ``timeout`` seconds."""
        with self.thread_lock:
            self.allow_process_request = False
            process = self.process
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None


class NoOpLazyProcess:
    """LazyProcess abstraction meant to describe potentially optional
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
