import pathlib
import sqlite3
import time

READ_ONLY_QUERY_TIMEOUT = 10.0
# Number of SQLite virtual machine instructions between deadline checks
_PROGRESS_HANDLER_INTERVAL = 1000

_READ_ONLY_ACTIONS = frozenset(
    (
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_FUNCTION,
        sqlite3.SQLITE_RECURSIVE,
    )
)


def _authorize_read_only(action, arg1, arg2, db_name, trigger_or_view):
    if action in _READ_ONLY_ACTIONS:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def connect(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def connect_read_only(path, timeout=READ_ONLY_QUERY_TIMEOUT):
    """Open ``path`` for running untrusted SELECT queries.

    The file is opened read-only and immutable, so SQLite takes no locks and
    creates no -wal/-shm files next to it. An authorizer refuses to prepare
    any statement that does more than read tables and call functions, which
    rules out ATTACH, PRAGMA, VACUUM INTO, transactions and writes.

    Statements still running ``timeout`` seconds after the connection is
    opened are interrupted with ``sqlite3.OperationalError("interrupted")``.
    """
    uri = f"{pathlib.Path(path).absolute().as_uri()}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.set_authorizer(_authorize_read_only)
    deadline = time.monotonic() + timeout
    connection.set_progress_handler(lambda: time.monotonic() > deadline, _PROGRESS_HANDLER_INTERVAL)
    return connection
