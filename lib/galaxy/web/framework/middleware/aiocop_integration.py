"""
aiocop integration — detect blocking I/O in async handlers.

`aiocop <https://github.com/Feverup/aiocop>`_ uses ``sys.audit`` hooks to catch
specific blocking syscalls (``socket.connect``, ``open``, ``subprocess.Popen``,
etc.) from within async tasks and report the exact call site.

This module installs aiocop and adds an ASGI middleware that surfaces any
violations recorded during a request via an ``X-Aiocop-Violations`` response
header so test harnesses can fail requests that block the event loop.

Activation is opt-in via the ``GALAXY_TEST_AIOCOP`` environment variable —
aiocop is a test-only dependency and is not imported in normal production
Galaxy servers.
"""

import asyncio
import logging
import os
import threading
from contextvars import ContextVar
from typing import (
    Any,
    Optional,
)

from starlette.types import (
    ASGIApp,
    Message,
    Receive,
    Scope,
    Send,
)

log = logging.getLogger(__name__)

ENV_VAR = "GALAXY_TEST_AIOCOP"

# High-severity threshold used by aiocop itself (THRESHOLD_HIGH == 50).
# Anything at or above is considered a test-failing violation.
HIGH_SEVERITY_SCORE = 50

_request_violations: ContextVar[Optional[list[dict[str, Any]]]] = ContextVar("aiocop_request_violations", default=None)

_process_initialized = False


def aiocop_enabled() -> bool:
    return os.environ.get(ENV_VAR, "").lower() in ("1", "true", "yes")


def _on_slow_task(event: Any) -> None:
    if not event.blocking_events:
        return
    violations = _request_violations.get()
    if violations is not None:
        violations.extend(event.blocking_events)
    log.error(
        "aiocop detected blocking I/O on event loop (severity=%s, elapsed=%.1fms): %s",
        event.severity_level,
        event.elapsed_ms,
        "; ".join(f"{e['event']} at {e['entry_point']}" for e in event.blocking_events),
    )


def install_aiocop(slow_task_threshold_ms: int = 50, trace_depth: int = 20) -> None:
    """Activate aiocop monitoring on the currently running event loop.

    Must be called from the event-loop thread (e.g. a FastAPI ``startup``
    event).  aiocop normally binds its audit hook to
    :func:`threading.main_thread`, but Galaxy's test harness runs uvicorn's
    event loop in a child thread — so we rebind the hook to the current
    thread explicitly.

    The Galaxy integration test driver spins up a fresh event loop on a new
    thread for every test module (see ``galaxy_test.driver.driver_util``).
    aiocop has process-global state — ``sys.addaudithook`` cannot be undone
    and ``patch_audit_functions`` wraps stdlib call sites in place — so we
    do that setup exactly once. The per-loop pieces (loop patching, main
    thread binding, slow-task callback) are re-armed on every call so the
    Nth Galaxy instance is actually monitored.
    """
    global _process_initialized

    import aiocop
    from aiocop.core import (
        blocking_io as _bio,
        slow_tasks as _slow_tasks,
    )

    if not _process_initialized:
        aiocop.patch_audit_functions()
        aiocop.start_blocking_io_detection(trace_depth=trace_depth)
        _process_initialized = True

    # aiocop binds audit events to the process main thread; the Galaxy test
    # server runs its event loop in a non-main thread, so pin aiocop to the
    # thread that actually hosts the loop.
    _bio._main_thread_id = threading.get_ident()

    # Re-arm detect_slow_tasks so the on-activate hook is fresh and the
    # slow-task callback isn't a stale closure from a prior Galaxy instance.
    # detect_slow_tasks() short-circuits on its module-global guard, so reset
    # it and clear the callback list before calling again.
    _slow_tasks._detect_slow_tasks_configured = False
    aiocop.clear_slow_task_callbacks()
    aiocop.detect_slow_tasks(threshold_ms=slow_task_threshold_ms, on_slow_task=_on_slow_task)
    aiocop.activate()
    log.info("aiocop blocking-I/O detection activated (threshold=%dms)", slow_task_threshold_ms)


class AiocopMiddleware:
    """Attach per-request aiocop violations to an ``X-Aiocop-Violations`` header.

    The header is only emitted when at least one blocking event was captured.
    Format:

        ``count=<n>;severity=<max>;first=<event>@<entry_point>``

    ``severity`` is the maximum severity weight among the captured events
    (see ``aiocop.core.blocking_io.BLOCKING_EVENTS_DICT``).  A value of
    50 or higher indicates a high-severity block that should fail tests.

    aiocop itself is installed on the first ``lifespan`` startup event so
    it binds to the event loop actually serving traffic (Galaxy's test
    harness runs uvicorn in a child thread — see
    :func:`galaxy_test.driver.driver_util.launch_server`).
    """

    def __init__(self, app: ASGIApp):
        self.app = app
        self._installed = False

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            # Wrap lifespan startup to install aiocop as soon as the loop
            # is running, before any request is served.
            async def send_wrapper(message: Message) -> None:
                if message.get("type") == "lifespan.startup.complete" and not self._installed:
                    install_aiocop()
                    self._installed = True
                await send(message)

            return await self.app(scope, receive, send_wrapper)

        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        violations: list[dict[str, Any]] = []
        token = _request_violations.set(violations)
        response_started = False

        async def send_with_header(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start" and not response_started:
                response_started = True
                # aiocop's slow-task callback fires when the task step that
                # did the blocking I/O ends; yield once to let any pending
                # callback populate `violations` before we emit headers.
                await asyncio.sleep(0)
                if violations:
                    max_severity = max(int(v.get("severity") or 0) for v in violations)
                    first = violations[0]
                    summary = (
                        f"count={len(violations)};severity={max_severity};"
                        f"first={first['event']}@{first['entry_point']}"
                    )
                    headers = list(message.get("headers", []))
                    headers.append((b"x-aiocop-violations", summary.encode("latin-1")))
                    message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            _request_violations.reset(token)
