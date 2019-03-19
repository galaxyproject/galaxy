import datetime
import threading

from galaxy.model import WorkerProcess
from galaxy.model.orm.now import now


class DatabaseHeartbeat(object):

    def __init__(self, sa_session, server_name=None, application_stack=None, heartbeat_interval=60):
        self.sa_session = sa_session
        self._server_name = server_name
        self.application_stack = application_stack
        self.heartbeat_interval = heartbeat_interval
        self.exit = threading.Event()
        self.thread = None
        self.active = False

    @property
    def server_name(self):
        # Application stack manipulates server name after forking
        return self.application_stack.app.config.server_name if self.application_stack else self._server_name

    def start(self):
        if not self.active:
            self.thread = threading.Thread(target=self.send_database_heartbeat, name="database_heartbeart_%s.thread" % self.server_name)
            self.thread.daemon = True
            self.active = True
            self.thread.start()

    def shutdown(self):
        self.active = False
        self.exit.set()
        if self.thread:
            self.thread.join()

    def get_active_processes(self, last_seen_seconds=None):
        """Return all processes seen in ``last_seen_seconds`` seconds."""
        if last_seen_seconds is None:
            last_seen_seconds = self.heartbeat_interval
        seconds_ago = now() - datetime.timedelta(seconds=last_seen_seconds)
        return self.sa_session.query(WorkerProcess).filter(WorkerProcess.table.c.update_time > seconds_ago).all()

    def send_database_heartbeat(self):
        if self.active:
            while not self.exit.isSet():
                worker_process = self.sa_session.query(WorkerProcess).filter_by(
                    server_name=self.server_name).first()
                if not worker_process:
                    worker_process = WorkerProcess(server_name=self.server_name)
                worker_process.update_time = now()
                self.sa_session.add(worker_process)
                self.sa_session.flush()
                self.exit.wait(self.heartbeat_interval)
