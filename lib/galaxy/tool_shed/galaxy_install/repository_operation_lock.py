"""Serialize tool shed repository operations across Galaxy processes and threads.

Installs (including updates), uninstalls, deactivations, activations and
metadata resets change the install database, the repository directories and
the shed tool and data manager confs together. Every Galaxy process that shares
the install database takes the same lock around these operations, so they run
one at a time and each one reads the confs only after the previous one has
written them.

On PostgreSQL the lock is a session-level advisory lock, held on a dedicated
autocommit connection from the install database engine. The server releases it
when that connection closes, including when the holding process dies. Other
databases use an ``flock`` on a file in ``data_dir``, which only serializes
processes on the same host. With a SQLite install database every Galaxy
process runs on one host anyway.

Operations take the lock before their first database write. A process that
waits for the lock while its own session holds uncommitted row locks could
deadlock with the holder, and PostgreSQL would not detect it, because the two
waits happen on different connections.
"""

import fcntl
import functools
import hashlib
import logging
import os
import threading
from collections.abc import (
    Callable,
    Iterator,
)
from contextlib import contextmanager
from typing import (
    Any,
    Concatenate,
    ParamSpec,
    TypeVar,
)

from sqlalchemy import text
from sqlalchemy.engine import Engine

log = logging.getLogger(__name__)

LOCK_FILE_NAME = "tool_shed_repository_operations.lock"
# pg_advisory_lock takes a signed 64-bit key. Deriving it from a name keeps it
# distinct from advisory locks taken by anything else in the same database.
ADVISORY_LOCK_KEY = int.from_bytes(
    hashlib.sha256(b"galaxy.tool_shed.repository_operation").digest()[:8], "big", signed=True
)

P = ParamSpec("P")
R = TypeVar("R")

# Locks this thread holds, keyed by lock identity, with their nesting depth.
_held = threading.local()


@contextmanager
def repository_operation_lock(app: Any) -> Iterator[None]:
    """Hold the repository operation lock of ``app``'s install database.

    Reentrant within a thread: an operation that runs another one (an install
    activating a repository dependency) keeps the lock it already holds.
    """
    engine = app.install_model.engine
    is_postgres = engine.dialect.name == "postgresql"
    identity = str(engine.url) if is_postgres else os.path.join(app.config.data_dir, LOCK_FILE_NAME)
    if not hasattr(_held, "depths"):
        _held.depths = {}
    depths: dict[str, int] = _held.depths
    if depths.get(identity):
        depths[identity] += 1
        try:
            yield
        finally:
            depths[identity] -= 1
        return
    acquire = _advisory_lock(engine) if is_postgres else _file_lock(identity)
    with acquire:
        depths[identity] = 1
        try:
            yield
        finally:
            del depths[identity]


def with_repository_operation_lock(
    method: Callable[Concatenate[Any, P], R],
) -> Callable[Concatenate[Any, P], R]:
    """Run a method of an object with an ``app`` attribute under the repository operation lock."""

    @functools.wraps(method)
    def wrapper(self: Any, *args: P.args, **kwargs: P.kwargs) -> R:
        with repository_operation_lock(self.app):
            return method(self, *args, **kwargs)

    return wrapper


@contextmanager
def _advisory_lock(engine: Engine) -> Iterator[None]:
    with engine.connect() as connection:
        connection.execution_options(isolation_level="AUTOCOMMIT")
        connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": ADVISORY_LOCK_KEY})
        try:
            yield
        finally:
            try:
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": ADVISORY_LOCK_KEY})
            except Exception:
                # The server already released the lock if it dropped the connection.
                log.exception("Failed to release the tool shed repository operation lock")


@contextmanager
def _file_lock(path: str) -> Iterator[None]:
    with open(path, "a") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        yield
