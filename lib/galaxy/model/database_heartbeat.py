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
from galaxy.model.base import check_database_connection
from galaxy.model.orm.now import now

log = logging.getLogger(__name__)

WEBAPP = "webapp"  # WorkerProcess.app_type for web apps.
SSE_MONITOR = "sse_monitor"  # WorkerProcess.app_type for the standalone SSE monitor process.
SSE_MONITOR_SERVER_PREFIX = "sse_monitor."  # server_name prefix used by the standalone SSE monitor process.


class DatabaseHeartbeat:
    def __init__(self, application_stack, heartbeat_interval=60):
        self.application_stack = application_stack
        self.new_session = self.application_stack.app.model.new_session
        self.heartbeat_interval = heartbeat_interval
        self.hostname = socket.gethostname()
        self._engine = application_stack.app.model.engine
        self._is_config_watcher = False
        self._is_history_audit_monitor = False
        self._observers = []
        self._audit_monitor_observers = []
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

    def add_audit_monitor_change_callback(self, callback):
        self._audit_monitor_observers.append(callback)

    @property
    def is_config_watcher(self):
        return self._is_config_watcher

    @is_config_watcher.setter
    def is_config_watcher(self, value):
        self._is_config_watcher = value
        log.debug("%s %s config watcher", self.server_name, "is" if self.is_config_watcher else "is not")
        for callback in self._observers:
            callback(self._is_config_watcher)

    @property
    def is_history_audit_monitor(self):
        return self._is_history_audit_monitor

    @is_history_audit_monitor.setter
    def is_history_audit_monitor(self, value):
        self._is_history_audit_monitor = value
        log.debug(
            "%s %s history audit monitor",
            self.server_name,
            "is" if self._is_history_audit_monitor else "is not",
        )
        for callback in self._audit_monitor_observers:
            callback(self._is_history_audit_monitor)

    def _app_type(self):
        if self.application_stack.app.is_webapp:
            return WEBAPP
        if self.server_name.startswith(SSE_MONITOR_SERVER_PREFIX):
            return SSE_MONITOR
        return None

    def update_watcher_designation(self):
        expression = self._worker_process_identifying_clause()
        stmt = select(WorkerProcess).with_for_update(of=WorkerProcess).where(expression)
        with self.new_session() as session, session.begin():
            worker_process = session.scalars(stmt).first()
            if not worker_process:
                worker_process = WorkerProcess(server_name=self.server_name, hostname=self.hostname)
            app_type = self._app_type()
            if app_type is not None:
                worker_process.app_type = app_type
            worker_process.update_time = now()
            worker_process.pid = self.pid
            session.add(worker_process)
        active = list(self.get_active_processes(self.heartbeat_interval + 1))
        # We only want a single process watching the various config files on the file system.
        # We just pick the max server name for simplicity
        webapp_servers = [p.server_name for p in active if p.app_type == WEBAPP]
        is_config_watcher = bool(webapp_servers) and self.server_name == max(webapp_servers)
        if is_config_watcher != self.is_config_watcher:
            self.is_config_watcher = is_config_watcher
        # The history-audit monitor is a single elected process too, but preference
        # goes to a standalone sse_monitor daemon when one is running so the
        # monitor's postgres LISTEN isn't blocked by webapp GIL pauses. If no
        # dedicated process is registered we fall back to a webapp (same
        # max-server_name tiebreaker as config_watcher).
        audit_leader = self._elect_audit_leader(active, webapp_servers)
        is_history_audit_monitor = audit_leader is not None and self.server_name == audit_leader
        if is_history_audit_monitor != self.is_history_audit_monitor:
            self.is_history_audit_monitor = is_history_audit_monitor

    @staticmethod
    def _elect_audit_leader(active, webapp_servers):
        monitor_servers = [p.server_name for p in active if p.app_type == SSE_MONITOR]
        if monitor_servers:
            return min(monitor_servers)
        if webapp_servers:
            return max(webapp_servers)
        return None

    def send_database_heartbeat(self):
        if self.active:
            while not self.exit.is_set():
                check_database_connection(self.sa_session)
                try:
                    self.update_watcher_designation()
                except Exception:
                    log.exception("Error sending database heartbeat for server '%s'", self.server_name)
                self.exit.wait(self.heartbeat_interval)

    def _delete_worker_process(self):
        expression = self._worker_process_identifying_clause()
        stmt = delete(WorkerProcess).where(expression)
        with self._engine.begin() as conn:
            conn.execute(stmt)

    def _worker_process_identifying_clause(self):
        return and_(WorkerProcess.server_name == self.server_name, WorkerProcess.hostname == self.hostname)
