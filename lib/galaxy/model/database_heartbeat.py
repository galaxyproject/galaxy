import datetime
import logging
import os
import socket
import threading

from sqlalchemy import (
    and_,
    delete,
    select,
)

from galaxy.model import WorkerProcess
from galaxy.model.orm.now import now

log = logging.getLogger(__name__)


class DatabaseHeartbeat:
    def __init__(self, application_stack, heartbeat_interval=60):
        self.application_stack = application_stack
        self.new_session = self.application_stack.app.model.new_session
        self.heartbeat_interval = heartbeat_interval
        self.hostname = socket.gethostname()
        self._engine = application_stack.app.model.engine
        self._is_config_watcher = False
        self._observers = []
        self.exit = threading.Event()
        self.thread = None
        self.active = False
        self.pid = None

    @property
    def sa_session(self):
        return self.application_stack.app.model.session

    @property
    def server_name(self):
        # Application stack manipulates server name after forking
        return self.application_stack.app.config.server_name

    def start(self):
        if not self.active:
            self.thread = threading.Thread(
                target=self.send_database_heartbeat, name=f"database_heartbeart_{self.server_name}.thread"
            )
            self.thread.daemon = True
            self.active = True
            self.thread.start()
            self.pid = os.getpid()

    def shutdown(self):
        self.active = False
        self.exit.set()
        if self.thread:
            self.thread.join()
        self._delete_worker_process()
        self.application_stack.app.queue_worker.send_control_task("reconfigure_watcher", noop_self=True)

    def get_active_processes(self, last_seen_seconds=None):
        """Return all processes seen in ``last_seen_seconds`` seconds."""
        if last_seen_seconds is None:
            last_seen_seconds = self.heartbeat_interval
        seconds_ago = now() - datetime.timedelta(seconds=last_seen_seconds)
        stmt = select(WorkerProcess).filter(WorkerProcess.update_time > seconds_ago)
        with self.new_session() as session:
            return session.scalars(stmt).all()

    def add_change_callback(self, callback):
        self._observers.append(callback)

    @property
    def is_config_watcher(self):
        return self._is_config_watcher

    @is_config_watcher.setter
    def is_config_watcher(self, value):
        self._is_config_watcher = value
        log.debug("%s %s config watcher", self.server_name, "is" if self.is_config_watcher else "is not")
        for callback in self._observers:
            callback(self._is_config_watcher)

    def update_watcher_designation(self):
        expression = self._worker_process_identifying_clause()
        stmt = select(WorkerProcess).with_for_update(of=WorkerProcess).where(expression)
        with self.new_session() as session, session.begin():
            worker_process = session.scalars(stmt).first()
            if not worker_process:
                worker_process = WorkerProcess(server_name=self.server_name, hostname=self.hostname)
            worker_process.update_time = now()
            worker_process.pid = self.pid
            session.add(worker_process)
        # We only want a single process watching the various config files on the file system.
        # We just pick the max server name for simplicity
        is_config_watcher = self.server_name == max(
            p.server_name for p in self.get_active_processes(self.heartbeat_interval + 1)
        )
        if is_config_watcher != self.is_config_watcher:
            self.is_config_watcher = is_config_watcher

    def send_database_heartbeat(self):
        if self.active:
            while not self.exit.is_set():
                self.update_watcher_designation()
                self.exit.wait(self.heartbeat_interval)

    def _delete_worker_process(self):
        expression = self._worker_process_identifying_clause()
        stmt = delete(WorkerProcess).where(expression)
        with self._engine.begin() as conn:
            conn.execute(stmt)

    def _worker_process_identifying_clause(self):
        return and_(WorkerProcess.server_name == self.server_name, WorkerProcess.hostname == self.hostname)
