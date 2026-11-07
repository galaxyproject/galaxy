import pathlib
import sqlite3

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


def connect_read_only(path):
    """Open ``path`` for running untrusted SELECT queries.

    The file is opened read-only and immutable, so SQLite takes no locks and
    creates no -wal/-shm files next to it. An authorizer refuses to prepare
    any statement that does more than read tables and call functions, which
    rules out ATTACH, PRAGMA, VACUUM INTO, transactions and writes.
    """
    uri = f"{pathlib.Path(path).absolute().as_uri()}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.set_authorizer(_authorize_read_only)
    return connection
