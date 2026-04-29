"""Entry point for the standalone ``galaxy-sse-monitor`` daemon.

Loads a minimal :class:`GalaxyManagerApplication` (same shape the Celery
workers use), forces the server_name to ``sse_monitor.<host>.<pid>`` so
DatabaseHeartbeat's election picks this process as the history-audit monitor,
and blocks on SIGINT/SIGTERM.
"""

import logging
import os
import signal
import socket
import sys
import threading

from galaxy.celery import get_app_properties
from galaxy.model.database_heartbeat import DatabaseHeartbeat

log = logging.getLogger("galaxy.sse_monitor")


def _build_server_name() -> str:
    return f"sse_monitor.{socket.gethostname()}.{os.getpid()}"


def _build_app(server_name: str):
    kwargs = get_app_properties() or {}
    if not kwargs:
        raise RuntimeError(
            "GALAXY_CONFIG_FILE (or GALAXY_ROOT_DIR with an on-disk Galaxy config) is required "
            "to start galaxy-sse-monitor"
        )
    kwargs = dict(kwargs)
    kwargs["check_migrate_databases"] = False
    kwargs["use_display_applications"] = False
    kwargs["use_converters"] = False
    kwargs["server_name"] = server_name

    import galaxy.app

    return galaxy.app.GalaxyManagerApplication(configure_logging=True, **kwargs)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    server_name = _build_server_name()
    log.info("Starting galaxy-sse-monitor as %s", server_name)

    app = _build_app(server_name)

    # GalaxyManagerApplication doesn't wire a DatabaseHeartbeat (that lives on
    # UniverseApplication, which pulls in the webapp stack we don't need). We
    # spin up our own and register the audit-monitor callback so election
    # transitions start/stop the producer cleanly.
    heartbeat = DatabaseHeartbeat(application_stack=app.application_stack)

    monitor = None
    if app.config.enable_sse_updates:
        from galaxy.managers.history_audit_monitor import HistoryAuditMonitor

        monitor = app[HistoryAuditMonitor]
        heartbeat.add_audit_monitor_change_callback(monitor.on_role_change)
    else:
        log.warning("enable_sse_updates is False — galaxy-sse-monitor will idle with no producers")

    heartbeat.start()

    shutdown = threading.Event()

    def _handle_signal(signum, _frame):
        log.info("Received signal %s, shutting down galaxy-sse-monitor", signum)
        shutdown.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        shutdown.wait()
    finally:
        if monitor is not None:
            try:
                monitor.shutdown()
            except Exception:
                log.exception("Error shutting down HistoryAuditMonitor")
        try:
            heartbeat.shutdown()
        except Exception:
            log.exception("Error shutting down database heartbeat")
        try:
            app.shutdown()
        except Exception:
            log.exception("Error shutting down GalaxyManagerApplication")

    return 0


if __name__ == "__main__":
    sys.exit(main())
