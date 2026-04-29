"""Shared helpers for SSE integration tests.

The stream layer emits a ``ready`` event as the first frame on every connection
so tests can synchronize on the server-side subscription rather than the
underlying TCP socket. ``SSELineListener`` waits for that ``ready`` event before
``start()`` returns, and propagates listener-thread exceptions back to the main
thread instead of silently swallowing them.
"""

import queue
import threading
from collections.abc import Callable
from typing import Optional

import requests

from galaxy.util.wait import wait_on

CONNECT_TIMEOUT = 15
DEFAULT_WAIT_TIMEOUT = 15


def parse_sse_events(raw: str) -> list[dict]:
    """Parse raw SSE text into a list of event dicts with ``event``, ``data``, and ``id`` keys."""
    events: list[dict] = []
    current: dict[str, str] = {}
    for line in raw.split("\n"):
        if line.startswith(":"):
            continue  # comment / keepalive
        if line == "":
            if current:
                events.append(current)
                current = {}
            continue
        if ": " in line:
            field, _, value = line.partition(": ")
        else:
            field, value = line.rstrip(":"), ""
        if field in ("event", "data", "id"):
            current[field] = value
    if current:
        events.append(current)
    return events


class SSEListenerError(Exception):
    """Wraps an exception raised inside the listener thread."""


class SSELineListener:
    """Runs an SSE connection on a background thread and collects raw chunks.

    ``start()`` blocks until the server-side ``ready`` event has been received,
    guaranteeing that any event *posted after* ``start()`` returns will be seen
    by this listener. Failures in the background thread are surfaced via
    ``wait_for_event`` instead of silently timing out.
    """

    def __init__(
        self,
        url: str,
        api_key: str,
        headers: Optional[dict] = None,
        timeout: int = 30,
    ) -> None:
        self.url = url
        self.api_key = api_key
        self.headers = headers or {}
        self.timeout = timeout
        self._collected: list[str] = []
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._errors: queue.Queue[BaseException] = queue.Queue()
        self._thread = threading.Thread(target=self._listen, daemon=True)

    def start(self) -> None:
        self._thread.start()
        wait_on(
            lambda: True if self._ready.is_set() else None,
            "SSE `ready` event",
            timeout=CONNECT_TIMEOUT,
        )
        self._raise_if_errored()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def wait_for_event(self, event_type: str, timeout: int = DEFAULT_WAIT_TIMEOUT) -> list[dict]:
        """Block until at least one event of ``event_type`` has been observed, then return all such events."""

        def _check():
            self._raise_if_errored()
            events = self.get_events(event_type)
            return events if events else None

        return wait_on(_check, f"SSE {event_type} event", timeout=timeout)

    def wait_for_event_where(
        self,
        event_type: str,
        predicate: Callable[[dict], bool],
        timeout: int = DEFAULT_WAIT_TIMEOUT,
    ) -> list[dict]:
        """Block until at least one ``event_type`` event matches ``predicate``.

        Returns every ``event_type`` event observed so far, not just matches, so
        callers can still inspect the surrounding stream (e.g. assert what else
        did or didn't appear) after the wait resolves.
        """

        def _check():
            self._raise_if_errored()
            events = self.get_events(event_type)
            return events if any(predicate(e) for e in events) else None

        return wait_on(_check, f"SSE {event_type} matching predicate", timeout=timeout)

    def get_events(self, event_type: Optional[str] = None) -> list[dict]:
        """Return all collected events so far, optionally filtered by type."""
        all_events = parse_sse_events("".join(self._collected))
        if event_type is None:
            return all_events
        return [e for e in all_events if e.get("event") == event_type]

    def _raise_if_errored(self) -> None:
        try:
            err = self._errors.get_nowait()
        except queue.Empty:
            return
        raise SSEListenerError(f"SSE listener thread failed: {err!r}") from err

    def _listen(self) -> None:
        try:
            resp = requests.get(
                self.url,
                params={"key": self.api_key},
                headers=self.headers,
                stream=True,
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"SSE connect returned HTTP {resp.status_code}: {resp.text[:200]}")
            for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
                if chunk:
                    self._collected.append(chunk)
                    if not self._ready.is_set() and "event: ready" in "".join(self._collected):
                        self._ready.set()
                if self._stop.is_set():
                    break
            resp.close()
        except Exception as exc:
            self._errors.put(exc)
            # Ensure start() doesn't hang forever on connection failure.
            self._ready.set()
