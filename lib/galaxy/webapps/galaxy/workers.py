"""Gunicorn worker class used to run the Galaxy ASGI application.

uvicorn's gunicorn worker makes two choices that together turn an ordinary worker
recycle (``--max-requests``) into an unexplained core dump:

- ``Server.shutdown()`` waits indefinitely for in-flight requests, because
  ``timeout_graceful_shutdown`` is never set, and it stops notifying the arbiter
  while it waits (``callback_notify`` only fires from ``main_loop``, which has
  already exited). The arbiter eventually decides the worker is hung.
- ``init_signals()`` resets ``SIGABRT`` to ``SIG_DFL``, so the arbiter's timeout
  kill dumps core instead of running gunicorn's ``worker_abort`` hook, and skips
  the ``atexit`` handler that shuts Galaxy down.

This worker bounds the drain, puts the ``SIGABRT`` handler back, and reports what
was still in flight whenever a worker is torn down the hard way.
"""

import asyncio
import io
import logging
import signal
import sys
import threading
import time
import traceback
from types import FrameType
from typing import (
    Any,
    Optional,
)

from gunicorn.arbiter import Arbiter
from uvicorn.server import Server

log = logging.getLogger(__name__)

try:
    import uvloop  # noqa: F401
    from uvicorn.workers import UvicornWorker as _BaseWorker
except ImportError:
    log.warning("uvloop not available, falling back to pure python worker")
    from uvicorn.workers import UvicornH11Worker as _BaseWorker

#: How often to report on a drain that is still in progress.
DRAIN_REPORT_INTERVAL = 10
#: How often the drain reporter wakes up.
DRAIN_POLL_INTERVAL = 0.25
#: How far ahead of uvicorn's own cancellation to report the requests it will cancel.
DRAIN_DEADLINE_LEAD = 1.0
#: Frames to keep per thread in the stack dump.
STACK_FRAME_LIMIT = 30


def _interesting_frame(frames):
    """Innermost frame inside Galaxy, falling back to the innermost frame.

    Same heuristic as ``galaxy.util.heartbeat.Heartbeat.get_interesting_stack_frame``.
    """
    for frame in reversed(frames):
        idx = frame.filename.find("/lib/galaxy/")
        if idx != -1:
            return f"{frame.filename[idx:]}:{frame.lineno} in {frame.name}"
    if frames:
        return f"{frames[-1].filename}:{frames[-1].lineno} in {frames[-1].name}"
    return "<no frames>"


def _task_frames(task):
    """Frames of the coroutine chain a task is suspended in, outermost first.

    ``Task.get_stack()`` returns only the outermost coroutine frame for a suspended
    task, which is always uvicorn's ``run_asgi``; walking ``cr_await`` recovers the
    awaits underneath it, where the request actually is.
    """
    frames: list[FrameType] = []
    awaitable = task.get_coro()
    seen = set()
    while awaitable is not None and len(frames) < STACK_FRAME_LIMIT and id(awaitable) not in seen:
        seen.add(id(awaitable))
        frame = (
            getattr(awaitable, "cr_frame", None)
            or getattr(awaitable, "ag_frame", None)
            or getattr(awaitable, "gi_frame", None)
        )
        if frame is None:
            break
        frames.append(frame)
        awaitable = (
            getattr(awaitable, "cr_await", None)
            or getattr(awaitable, "ag_await", None)
            or getattr(awaitable, "gi_yieldfrom", None)
        )
    return traceback.StackSummary.extract((frame, frame.f_lineno) for frame in frames)


def _describe_connection(protocol, at_drain_start):
    scope = getattr(protocol, "scope", None) or {}
    method = scope.get("method", "?")
    path = scope.get("path", "?")
    if scope.get("query_string"):
        path = f"{path}?{scope['query_string'].decode('ascii', 'replace')}"
    client = scope.get("client")
    client = f"{client[0]}:{client[1]}" if client else "?"
    cycle = getattr(protocol, "cycle", None)
    return (
        f"{method} {path} client={client}"
        f" response_started={getattr(cycle, 'response_started', '?')}"
        f" response_complete={getattr(cycle, 'response_complete', '?')}"
        f" present_at_drain_start={protocol in at_drain_start}"
    )


class _Server(Server):
    """uvicorn ``Server`` that reports on a graceful shutdown while it runs.

    ``should_exit`` is not usable for this: on the ``--max-requests`` path
    ``on_tick`` returns true without ever setting it, which is precisely the case
    worth reporting on.
    """

    def __init__(self, config, worker):
        super().__init__(config=config)
        self._worker = worker

    async def shutdown(self, sockets=None):
        reporter = asyncio.ensure_future(self._worker.report_drain(self))
        try:
            await super().shutdown(sockets=sockets)
        finally:
            reporter.cancel()


class Worker(_BaseWorker):
    """Galaxy's gunicorn worker. Referenced by name in gravity and startup scripts."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._uvicorn_server: Optional[Server] = None
        self._drain_started: Optional[float] = None
        self._connections_at_drain_start: frozenset[Any] = frozenset()
        if self.config.timeout_graceful_shutdown is None:
            # Without this uvicorn drains forever while no longer notifying the
            # arbiter, so a recycle that catches a long-running request always ends
            # in SIGABRT. graceful_timeout is gunicorn's name for exactly this bound.
            self.config.timeout_graceful_shutdown = self.cfg.graceful_timeout
        # The arbiter aborts `timeout` seconds after the last notify, and the last
        # notify can be up to `self.timeout` (half of cfg.timeout) before the drain
        # begins, so this is the earliest an abort can land.
        earliest_abort = self.cfg.timeout - self.timeout
        if self.cfg.timeout and self.config.timeout_graceful_shutdown >= earliest_abort:
            log.warning(
                "Gunicorn graceful_timeout (%ss) leaves no room under timeout (%ss): a worker draining "
                "in-flight requests can still be aborted by the arbiter after %ss. Lower graceful_timeout "
                "or raise timeout.",
                self.config.timeout_graceful_shutdown,
                self.cfg.timeout,
                earliest_abort,
            )

    def init_signals(self):
        super().init_signals()
        # uvicorn resets every signal gunicorn handles to SIG_DFL. For SIGABRT --
        # which the arbiter sends when a worker misses its timeout -- the default
        # disposition is a core dump, which skips both the worker_abort hook and
        # every atexit handler. Put gunicorn's own handler back.
        signal.signal(signal.SIGABRT, self.handle_abort)

    async def _serve(self):
        # Mirrors uvicorn.workers.UvicornWorker._serve; copied so the Server can be
        # kept, as nothing else exposes its connection and task state.
        self.config.app = self.wsgi
        server = _Server(config=self.config, worker=self)
        self._uvicorn_server = server
        self._install_sigquit_handler()
        await server.serve(sockets=self.sockets)
        if not server.started:
            sys.exit(Arbiter.WORKER_BOOT_ERROR)

    async def report_drain(self, server):
        """Log what is holding a graceful shutdown open, while it is still open."""
        try:
            await self._report_drain_loop(server)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Graceful shutdown reporter failed")

    async def _report_drain_loop(self, server):
        self._drain_started = time.monotonic()
        self._connections_at_drain_start = frozenset(server.server_state.connections)
        next_report = DRAIN_REPORT_INTERVAL
        reported_deadline = False
        configured_deadline = self.config.timeout_graceful_shutdown
        # Report just before uvicorn cancels rather than at the same instant, or the
        # report loses the race and the requests that were killed go unrecorded.
        deadline = max(0.0, configured_deadline - DRAIN_DEADLINE_LEAD) if configured_deadline is not None else None
        while True:
            await asyncio.sleep(DRAIN_POLL_INTERVAL)
            if not (server.server_state.connections or server.server_state.tasks):
                return
            elapsed = time.monotonic() - self._drain_started
            if deadline is not None and elapsed >= deadline and not reported_deadline:
                reported_deadline = True
                # These requests are about to be cancelled: WARNING carries the detail
                # into the log, ERROR raises a Sentry event with it as breadcrumbs.
                log.warning("Graceful shutdown deadline reached, stacks follow\n%s", self.in_flight_stacks())
                log.error("Graceful shutdown deadline reached, cancelling requests\n%s", self.in_flight_summary())
            elif elapsed >= next_report:
                next_report += DRAIN_REPORT_INTERVAL
                log.warning("Graceful shutdown still waiting\n%s", self.in_flight_summary())

    def in_flight_summary(self):
        """Compact description of what this worker is still serving.

        Kept small enough to survive as a Sentry event message. Called from a signal
        handler on the abort path, so it must never raise.
        """
        out = io.StringIO()
        try:
            server = self._uvicorn_server
            out.write(f"worker pid={self.pid} id={getattr(self, '_worker_id', '?')}")
            if server is None:
                out.write(" (uvicorn server not started)\n")
                return out.getvalue()
            state = server.server_state
            out.write(
                f" requests_served={state.total_requests} max_requests={self.config.limit_max_requests}"
                f" should_exit={server.should_exit}"
            )
            if self._drain_started is not None:
                out.write(f" draining_for={time.monotonic() - self._drain_started:.1f}s")
            out.write(f"\n{len(state.connections)} open connection(s):\n")
            for protocol in list(state.connections):
                out.write(f"  {_describe_connection(protocol, self._connections_at_drain_start)}\n")
            out.write(f"{len(state.tasks)} running request task(s):\n")
            for task in list(state.tasks):
                out.write(f"  {_interesting_frame(_task_frames(task))}\n")
        except Exception as e:
            out.write(f"\n<failed to summarize in-flight requests: {e!r}>\n")
        return out.getvalue()

    def in_flight_stacks(self):
        """Full stacks for the request tasks and every thread.

        The thread pass is the important one: Galaxy's sync and legacy WSGI endpoints
        run in a threadpool, so a request task stack usually bottoms out at
        ``run_in_threadpool`` and the code that is actually stuck is only visible here.
        """
        out = io.StringIO()
        try:
            server = self._uvicorn_server
            if server is not None:
                for task in list(server.server_state.tasks):
                    out.write(f"--- request task {task.get_name()}\n")
                    out.write("".join(_task_frames(task).format()))
            names = {t.ident: t.name for t in threading.enumerate()}
            out.write("--- thread stacks\n")
            for thread_id, frame in sys._current_frames().items():
                out.write(f"--- thread {thread_id} ({names.get(thread_id, '<unknown>')})\n")
                out.write("".join(traceback.format_stack(frame, limit=STACK_FRAME_LIMIT)))
        except Exception as e:
            out.write(f"\n<failed to dump stacks: {e!r}>\n")
        return out.getvalue()
