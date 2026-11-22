"""Shared helpers for SSE integration tests.

The stream layer emits a ``ready`` event as the first frame on every connection
so tests can synchronize on the server-side subscription rather than the
underlying TCP socket. ``SSELineListener`` waits for that ``ready`` event before
``start()`` returns, and propagates listener-thread exceptions back to the main
thread instead of silently swallowing them.
"""

import queue
import socket
import threading
import time
from collections.abc import Callable
from typing import TypeVar

import requests

from galaxy.util.wait import (
    timeout_type,
    TimeoutAssertionError,
)

T = TypeVar("T")

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
        headers: dict | None = None,
        timeout: int = 30,
    ) -> None:
        self.url = url
        self.api_key = api_key
        self.headers = headers or {}
        self.timeout = timeout
        self._collected: list[str] = []
        # Notified whenever a chunk arrives or the reading thread ends.
        self._received = threading.Condition()
        self._response: requests.Response | None = None
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._errors: queue.Queue[BaseException] = queue.Queue()
        self._thread = threading.Thread(target=self._listen, daemon=True)

    def start(self) -> None:
        self._thread.start()
        if not self._ready.wait(CONNECT_TIMEOUT):
            raise TimeoutAssertionError(f"Timed out after {CONNECT_TIMEOUT} seconds waiting on SSE `ready` event")
        self._raise_if_errored()

    def stop(self) -> None:
        self._stop.set()
        # The reading thread blocks until the next chunk, which may be a keepalive 30 seconds away;
        # shutting the socket down ends that read now.
        connection = self._response.raw.connection if self._response is not None else None
        if connection is not None and connection.sock is not None:
            try:
                connection.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self._thread.join(timeout=5)

    def wait_for_event(self, event_type: str, timeout: int = DEFAULT_WAIT_TIMEOUT) -> list[dict]:
        """Block until at least one event of ``event_type`` has been observed, then return all such events."""
        return self.wait_for_event_where(event_type, lambda event: True, timeout=timeout)

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
        if not self.wait_for_matching_event_count_above(event_type, predicate, 0, timeout):
            raise TimeoutAssertionError(
                f"Timed out after {timeout} seconds waiting on SSE {event_type} matching predicate"
            )
        return self.get_events(event_type)

    def matching_event_count(self, event_type: str, predicate: Callable[[dict], bool]) -> int:
        """Return how many ``event_type`` events matching ``predicate`` have arrived so far."""
        self._raise_if_errored()
        return sum(1 for event in self.get_events(event_type) if predicate(event))

    def wait_for_matching_event_count_above(
        self, event_type: str, predicate: Callable[[dict], bool], count: int, timeout: timeout_type
    ) -> bool:
        """Block until more than ``count`` matching events arrived; return ``False`` on timeout."""
        deadline = time.monotonic() + timeout
        with self._received:
            while self.matching_event_count(event_type, predicate) <= count:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._received.wait(remaining)
        return True

    def get_events(self, event_type: str | None = None) -> list[dict]:
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
            self._response = resp
            if resp.status_code != 200:
                raise RuntimeError(f"SSE connect returned HTTP {resp.status_code}: {resp.text[:200]}")
            for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
                if chunk:
                    with self._received:
                        self._collected.append(chunk)
                        self._received.notify_all()
                    if not self._ready.is_set() and "event: ready" in "".join(self._collected):
                        self._ready.set()
                if self._stop.is_set():
                    break
            resp.close()
        except Exception as exc:
            if not self._stop.is_set():
                self._errors.put(exc)
            # Ensure start() doesn't hang forever on connection failure.
            self._ready.set()
        finally:
            with self._received:
                self._received.notify_all()


def wait_on_events(
    listener: SSELineListener,
    event_type: str,
    predicate: Callable[[dict], bool],
    function: Callable[[], T | None],
    desc: str,
    timeout: timeout_type,
) -> T:
    """Like ``wait_on``, but re-runs ``function`` only when a matching event arrives instead of polling.

    ``function`` runs once up front, so ``listener`` must be started before the call: a change
    committed after that first run then always produces an event the listener sees. A missing
    event makes the wait time out, which is how tests using this exercise the event's producer.
    """
    deadline = time.monotonic() + timeout
    while True:
        seen = listener.matching_event_count(event_type, predicate)
        result = function()
        if result is not None:
            return result
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not listener.wait_for_matching_event_count_above(event_type, predicate, seen, remaining):
            raise TimeoutAssertionError(
                f"Timed out after {timeout} seconds waiting on {desc} (woken by SSE {event_type} events)."
            )
