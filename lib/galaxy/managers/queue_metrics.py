"""Periodic gauge emitter for control-queue depth and worker-process counts.

Scheduled by Celery beat (see ``galaxy.celery.__init__.setup_periodic_tasks``)
at a fixed cadence. Opens a short-lived kombu connection, iterates the control
queues returned by ``all_control_queues_for_declare`` and samples each queue's
message-count via a passive declare. Also samples the active-``WorkerProcess``
count from the database.

SSE connection counts are deliberately *not* sampled here: the
``SSEConnectionManager`` is per-process state held by the web workers, so the
Celery worker would only ever see an empty manager. Each web worker emits its
own ``galaxy.sse.connections.active`` gauge instead (see
``galaxy.managers.sse.SSEConnectionGaugeEmitter``).

All instrumentation no-ops when ``statsd_client`` is ``None`` — i.e. statsd
isn't configured.

The sub-emitters take narrow, typed collaborators (a kombu connection, an
application stack, a model mapping, the statsd client) rather than the whole
``StructuredApp``. The Celery task in
``galaxy.celery.tasks.emit_queue_metrics_task`` is the composition root that
resolves those narrow deps from the app and passes them in.
"""

import datetime
import logging
from collections import defaultdict
from collections.abc import Callable
from typing import (
    TYPE_CHECKING,
)

from sqlalchemy import (
    func,
    select,
)

from galaxy.model import WorkerProcess
from galaxy.model.mapping import GalaxyModelMapping
from galaxy.queues import (
    all_control_queues_for_declare,
    DEFAULT_ACTIVE_PROCESS_WINDOW_SECONDS,
)
from galaxy.util import now
from galaxy.web_stack import ApplicationStack

if TYPE_CHECKING:
    from kombu import Connection

    from galaxy.web.statsd_client import VanillaGalaxyStatsdClient

log = logging.getLogger(__name__)


def emit_control_queue_depth(
    statsd_client: "VanillaGalaxyStatsdClient",
    connection: "Connection | None",
    application_stack: ApplicationStack,
) -> None:
    """Emit ``galaxy.control_queue.depth`` per active webapp/handler queue.

    A per-queue passive declare can fail on transports that don't implement it
    (e.g. the sqlalchemy kombu transport) or for queues that don't yet exist on
    the broker. Those are expected and quiet — logged at DEBUG, no metric, move
    on. Errors at the broker-connection layer propagate up so the caller can
    surface them.
    """
    if connection is None:
        return
    queues = all_control_queues_for_declare(application_stack)
    if not queues:
        return
    with connection.clone() as conn:
        channel = conn.channel()
        try:
            for queue in queues:
                try:
                    declared = queue.bind(channel).queue_declare(passive=True)
                except Exception:
                    log.debug(
                        "queue_metrics: passive declare failed for %s",
                        queue.name,
                        exc_info=True,
                    )
                    continue
                statsd_client.gauge(
                    "galaxy.control_queue.depth",
                    declared.message_count,
                    tags={"queue_name": queue.name},
                )
        finally:
            channel.close()


def emit_worker_process_gauge(
    statsd_client: "VanillaGalaxyStatsdClient",
    model: GalaxyModelMapping,
) -> None:
    """Emit ``galaxy.worker_process.active`` gauge grouped by ``app_type``."""
    cutoff = now() - datetime.timedelta(seconds=DEFAULT_ACTIVE_PROCESS_WINDOW_SECONDS)
    stmt = (
        select(WorkerProcess.app_type, func.count(WorkerProcess.id))
        .where(WorkerProcess.update_time > cutoff)
        .group_by(WorkerProcess.app_type)
    )
    counts: dict[str, int] = defaultdict(int)
    with model.new_session() as session:
        for app_type, count in session.execute(stmt):
            counts[app_type or "unknown"] = int(count)
    for app_type, count in counts.items():
        statsd_client.gauge(
            "galaxy.worker_process.active",
            count,
            tags={"app_type": app_type},
        )


def _run(name: str, statsd_client: "VanillaGalaxyStatsdClient", fn: Callable[[], None]) -> None:
    """Run a sub-emitter, isolating its failures.

    A broken sub-emitter logs once at WARNING and increments
    ``galaxy.queue_metrics.error`` (tagged by emitter name) so the failure is
    observable in metrics without the Celery-beat wrapper logging on every
    tick. The other sub-emitters continue to run on this tick.
    """
    try:
        fn()
    except Exception:
        log.warning("queue_metrics: %s emitter failed", name, exc_info=True)
        statsd_client.incr("galaxy.queue_metrics.error", tags={"emitter": name})


def emit_queue_metrics(
    statsd_client: "VanillaGalaxyStatsdClient | None",
    connection: "Connection | None",
    application_stack: ApplicationStack,
    model: GalaxyModelMapping,
) -> None:
    """Periodic entry-point — no-ops when statsd isn't configured."""
    if statsd_client is None:
        return
    _run(
        "control_queue_depth",
        statsd_client,
        lambda: emit_control_queue_depth(statsd_client, connection, application_stack),
    )
    _run("worker_process", statsd_client, lambda: emit_worker_process_gauge(statsd_client, model))
