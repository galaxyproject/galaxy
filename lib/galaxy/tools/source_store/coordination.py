"""Run a full populate in one of the processes sharing a tool source store.

Every Galaxy process that finds the index empty or stale at boot or on a
toolbox reload would otherwise scan and write the same tool tree at the same
time. :func:`populate_once` lets one process populate while the others wait,
with no limit on how long a populate may take: the holder renews its lease
while it works, and waiters take over only when the lease expires because its
holder died.
"""

import logging
import os
import socket
import threading
import time
import uuid
from collections.abc import Callable
from datetime import (
    datetime,
    timedelta,
)

from .interface import (
    PopulateLease,
    PopulateLeaseBusy,
    PopulateLeaseError,
)

log = logging.getLogger(__name__)

# Long enough to cover clock skew between hosts and a stalled renewal; a
# holder that died is taken over after at most this long.
LEASE_TTL = timedelta(seconds=120)
RENEW_INTERVAL_SECONDS = 20.0
POLL_INTERVAL_SECONDS = 1.0
WAIT_LOG_INTERVAL_SECONDS = 30.0


def populate_once(
    lease: PopulateLease | None,
    needs_population: Callable[[], bool],
    populate: Callable[[], None],
    *,
    peer_result_usable: Callable[[], bool] = lambda: True,
    ttl: timedelta = LEASE_TTL,
    renew_interval: float = RENEW_INTERVAL_SECONDS,
    poll_interval: float = POLL_INTERVAL_SECONDS,
) -> bool:
    """Run ``populate`` unless another process populates the store first.

    ``needs_population`` re-reads the store and reports whether a populate is
    still needed; it runs while holding the lease, so a process that waited
    for another one sees that process's result. If another process completed
    a populate while this one waited and ``peer_result_usable`` accepts the
    result, it is used even when ``needs_population`` would still ask for a
    populate: the same populate run again would not change its result.

    Returns ``True`` when this process ran ``populate``.
    """
    if lease is None:
        populate()
        return True
    holder = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
    try:
        populated_at = lease.last_populated_at()
    except PopulateLeaseError as e:
        # e.g. a server database whose operator has not created the lease table.
        log.warning("Cannot coordinate tool source store population with other processes; populating anyway: %s", e)
        populate()
        return True
    _wait_for_lease(lease, holder, ttl, poll_interval)

    populated = False
    try:
        with _LeaseRenewal(lease, holder, ttl, renew_interval):
            if not needs_population():
                return False
            if _populated_since(lease, populated_at) and peer_result_usable():
                log.info("Another Galaxy process populated the tool source store; using its index")
                return False
            populate()
            populated = True
            return True
    finally:
        try:
            lease.release(holder, populated)
        except PopulateLeaseError as e:
            # The lease expires on its own; waiters then take it over.
            log.warning("Releasing the tool source store populate lease failed: %s", e)


def _populated_since(lease: PopulateLease, populated_at: datetime | None) -> bool:
    try:
        return lease.last_populated_at() != populated_at
    except PopulateLeaseError as e:
        log.warning("Cannot tell whether another process populated the tool source store: %s", e)
        return False


def _wait_for_lease(lease: PopulateLease, holder: str, ttl: timedelta, poll_interval: float) -> None:
    started = time.monotonic()
    last_logged: float | None = None
    while True:
        try:
            if lease.try_acquire(holder, ttl):
                return
        except PopulateLeaseBusy as e:
            # e.g. the busy timeout expired on a slow shared filesystem; the
            # holder is still populating, so keep waiting for it.
            log.debug("Polling the tool source store populate lease failed: %s", e)
        now = time.monotonic()
        if last_logged is None or now - last_logged >= WAIT_LOG_INTERVAL_SECONDS:
            last_logged = now
            log.info(
                "Waiting for another Galaxy process to finish populating the tool source store (%d s)", now - started
            )
        time.sleep(poll_interval)


class _LeaseRenewal:
    """Renew ``holder``'s lease from a background thread while the block runs."""

    def __init__(self, lease: PopulateLease, holder: str, ttl: timedelta, interval: float) -> None:
        self._lease = lease
        self._holder = holder
        self._ttl = ttl
        self._interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="ToolSourcePopulateLease", daemon=True)

    def __enter__(self) -> None:
        self._thread.start()

    def __exit__(self, *exc_info: object) -> None:
        self._stop.set()
        self._thread.join()

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                if not self._lease.renew(self._holder, self._ttl):
                    log.warning("Another process took over the tool source store populate lease")
                    return
            except Exception:
                log.exception("Renewing the tool source store populate lease failed")
