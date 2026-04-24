"""Standalone SSE monitor process.

Runs the :class:`~galaxy.managers.history_audit_monitor.HistoryAuditMonitor`
(and, in principle, any future SSE event producer) in its own OS process so a
webapp's GIL pauses or fork-lifecycle events can never block history-update
dispatch. Webapps still consume SSE events normally; only the *producer* moves.

The process registers itself via :class:`~galaxy.model.database_heartbeat.DatabaseHeartbeat`
with a server_name beginning with ``sse_monitor.``. The heartbeat's
``is_history_audit_monitor`` election prefers any such process, so the monitor
automatically migrates here when this daemon is running. If it stops, a webapp
is re-elected within one heartbeat interval (~60s).

Starting the daemon
-------------------

Installed::

    GALAXY_CONFIG_FILE=/etc/galaxy/galaxy.yml galaxy-sse-monitor

From a source checkout::

    GALAXY_CONFIG_FILE=config/galaxy.yml python -m galaxy.sse_monitor

For production deployments, run under systemd / supervisord alongside the
webapp. A native ``gravity`` (``galaxyctl``) service type for this daemon is
tracked as a follow-up against the ``gravity`` package — until that lands,
either start the process via your process manager of choice, or omit it and
let a webapp fall back to the monitor role.
"""
