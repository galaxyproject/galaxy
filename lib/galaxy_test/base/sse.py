"""Shared helpers for tests against Galaxy's SSE event stream.

``SSEWaiter`` backs the populators' event-driven waits. The stream layer emits a ``ready`` event as the first frame on every connection
so tests can synchronize on the server-side subscription rather than the
underlying TCP socket. ``SSELineListener`` waits for that ``ready`` event before
``start()`` returns, and propagates listener-thread exceptions back to the main
thread instead of silently swallowing them.
"""

import json
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
    wait_on,
)
from .api import ApiTestInteractor

T = TypeVar("T")

CONNECT_TIMEOUT = 15
DEFAULT_WAIT_TIMEOUT = 15
# The stream sends a keepalive every 30 seconds; a longer read timeout keeps idle waits connected.
WAIT_READ_TIMEOUT = 60


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


def job_states_for(events: list[dict], job_id: str) -> list[str]:
    """States of job ``job_id`` across ``job_update`` events, in order."""
    return [
        job["state"] for event in events for job in json.loads(event["data"]).get("jobs", []) if job["id"] == job_id
    ]


def invocation_states_for(events: list[dict], invocation_id: str) -> list[str]:
    """States of invocation ``invocation_id`` across ``invocation_update`` events, in order."""
    return [
        invocation["state"]
        for event in events
        for invocation in json.loads(event["data"])["invocations"]
        if invocation["id"] == invocation_id
    ]


class SSEWaiter:
    """Waits that re-check a condition when the server reports a change instead of polling.

    Against a server with ``enable_sse_updates``, each wait opens the event stream for the
    interactor's current user and re-runs its function only when a matching event arrives, so a
    missing event fails the wait. Events go to the owner of the changed object's history; when
    someone else owns it, the wait subscribes the user as a viewer of that history for its
    duration. Without an interactor, against servers without SSE updates, and for anonymous
    users, the waits poll.
    """

    def __init__(self, interactor: ApiTestInteractor | None) -> None:
        self._interactor = interactor
        self._enabled: bool | None = None
        # Tests switch users by swapping the interactor's API key, so user ids are cached per key.
        self._user_ids_by_api_key: dict[str, str] = {}

    def wait_on_job(self, job_id: str, function: Callable[[], T | None], desc: str, timeout: timeout_type) -> T:
        def matches(event: dict) -> bool:
            data = json.loads(event["data"])
            return "resync" in data or any(job["id"] == job_id for job in data["jobs"])

        return self._wait("job_update", matches, function, desc, timeout, lambda: self._job_history_id(job_id))

    def wait_on_history_jobs(
        self, history_id: str, function: Callable[[], T | None], desc: str, timeout: timeout_type
    ) -> T:
        # Job events do not name the history, so any change to a job the user sees re-checks it.
        return self._wait("job_update", lambda event: True, function, desc, timeout, lambda: history_id)

    def wait_on_history(self, history_id: str, function: Callable[[], T | None], desc: str, timeout: timeout_type) -> T:
        return self._wait(
            "history_update",
            lambda event: history_id in json.loads(event["data"])["history_ids"],
            function,
            desc,
            timeout,
            lambda: history_id,
        )

    def wait_on_invocation(
        self, invocation_id: str, function: Callable[[], T | None], desc: str, timeout: timeout_type
    ) -> T:
        return self._wait(
            "invocation_update",
            lambda event: any(item["id"] == invocation_id for item in json.loads(event["data"])["invocations"]),
            function,
            desc,
            timeout,
            lambda: self._get(f"invocations/{invocation_id}")["history_id"],
        )

    def _wait(
        self,
        event_type: str,
        predicate: Callable[[dict], bool],
        function: Callable[[], T | None],
        desc: str,
        timeout: timeout_type,
        history_id: Callable[[], str | None],
    ) -> T:
        listener = self._listener()
        if listener is None:
            return wait_on(function, desc, timeout=timeout)
        viewed_history_id = None
        try:
            watched_history_id = history_id()
            if watched_history_id is not None and not self._owns_history(watched_history_id):
                # Sent through the same control queue as the events, so the subscription reaches the
                # workers ahead of the events for any change committed after this returns.
                self._subscribe(watched_history_id)
                viewed_history_id = watched_history_id
            return wait_on_events(listener, event_type, predicate, function, desc, timeout)
        finally:
            if viewed_history_id is not None:
                self._unsubscribe(viewed_history_id)
            listener.stop()

    def _listener(self) -> SSELineListener | None:
        interactor = self._interactor
        if interactor is None or interactor.api_key is None:
            return None
        if self._enabled is None:
            # Servers that predate SSE updates do not report the option.
            self._enabled = bool(self._get("configuration").get("enable_sse_updates"))
        if not self._enabled:
            return None
        listener = SSELineListener(f"{interactor.api_url}/events/stream", interactor.api_key, timeout=WAIT_READ_TIMEOUT)
        listener.start()
        return listener

    def _owns_history(self, history_id: str) -> bool:
        return self._get(f"histories/{history_id}", {"keys": "user_id"})["user_id"] == self._current_user_id()

    def _current_user_id(self) -> str:
        assert self._interactor is not None and self._interactor.api_key is not None
        api_key = self._interactor.api_key
        if api_key not in self._user_ids_by_api_key:
            self._user_ids_by_api_key[api_key] = self._get("users/current")["id"]
        return self._user_ids_by_api_key[api_key]

    def _job_history_id(self, job_id: str) -> str | None:
        return self._get(f"jobs/{job_id}")["history_id"]

    def _get(self, path: str, data: dict | None = None) -> dict:
        assert self._interactor is not None
        response = self._interactor.get(path, data=data or {})
        response.raise_for_status()
        return response.json()

    def _subscribe(self, history_id: str) -> None:
        assert self._interactor is not None
        response = self._interactor.post("events/history-subscriptions", {"history_ids": [history_id]}, json=True)
        assert response.status_code == 204, response.text

    def _unsubscribe(self, history_id: str) -> None:
        assert self._interactor is not None
        response = self._interactor.delete("events/history-subscriptions", {"history_ids": [history_id]}, json=True)
        assert response.status_code == 204, response.text
