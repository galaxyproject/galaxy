import sqlite3

import pytest

from galaxy.util import sqlite

ALLOWED_QUERIES = [
    ("SELECT * FROM foo", [(1, "a", "b"), (2, "c", "d")]),
    ("SELECT f.col1, f.col2 FROM foo AS f", [("a", "b"), ("c", "d")]),
    ("SELECT f.col1, b.col2 FROM foo AS f INNER JOIN bar AS b ON f.id = b.foo_id", [("a", "x")]),
    ("SELECT * FROM foo WHERE id IN (SELECT foo_id FROM bar)", [(1, "a", "b")]),
    ("SELECT * FROM foo_view", [("a",), ("c",)]),
    ("SELECT count(*), max(id), upper(min(col1)) FROM foo", [(2, 2, "A")]),
    ("WITH t AS (SELECT col1 FROM foo) SELECT * FROM t", [("a",), ("c",)]),
    ("WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c WHERE x < 3) SELECT x FROM c", [(1,), (2,), (3,)]),
    ("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name", [("bar",), ("foo",)]),
    ("SELECT 1 UNION SELECT 2", [(1,), (2,)]),
]

DENIED_QUERIES = [
    "INSERT INTO foo VALUES (3, 'e', 'f')",
    "UPDATE foo SET col1 = 'z'",
    "DELETE FROM foo",
    "DROP TABLE foo",
    "CREATE TABLE baz (x)",
    "CREATE TEMP TABLE baz (x)",
    "ALTER TABLE foo ADD COLUMN extra TEXT",
    "REINDEX",
    "ANALYZE",
    "VACUUM",
    "VACUUM INTO '{directory}/copy.sqlite'",
    "ATTACH DATABASE '{directory}/other.sqlite' AS other",
    "PRAGMA user_version = 5",
    "PRAGMA table_info(foo)",
    "SELECT * FROM pragma_table_info('foo')",
    "BEGIN",
    "SAVEPOINT s",
    "SELECT * FROM foo; DROP TABLE foo",
    "SELECT 1; SELECT 2",
]


@pytest.fixture
def db_path(tmp_path):
    directory = tmp_path / "data set?#1"
    directory.mkdir()
    path = directory / "dataset_1.dat"
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE foo (id INTEGER PRIMARY KEY, col1 TEXT, col2 TEXT);
        CREATE TABLE bar (id INTEGER PRIMARY KEY, foo_id INTEGER, col2 TEXT);
        CREATE INDEX bar_foo_id ON bar (foo_id);
        CREATE VIEW foo_view AS SELECT col1 FROM foo;
        INSERT INTO foo VALUES (1, 'a', 'b'), (2, 'c', 'd');
        INSERT INTO bar VALUES (1, 1, 'x');
        """)
    connection.close()
    return path


def _directory_contents(directory):
    return {path.name: path.read_bytes() for path in directory.iterdir()}


@pytest.mark.parametrize("query,rows", ALLOWED_QUERIES)
def test_connect_read_only_runs_select(db_path, query, rows):
    before = _directory_contents(db_path.parent)
    connection = sqlite.connect_read_only(db_path)
    assert [tuple(row) for row in connection.execute(query)] == rows
    connection.close()
    assert _directory_contents(db_path.parent) == before


@pytest.mark.parametrize("query", DENIED_QUERIES)
def test_connect_read_only_refuses_non_select(db_path, query):
    before = _directory_contents(db_path.parent)
    connection = sqlite.connect_read_only(db_path)
    with pytest.raises((sqlite3.Error, sqlite3.Warning)):
        connection.execute(query.format(directory=db_path.parent))
    connection.commit()
    connection.close()
    assert _directory_contents(db_path.parent) == before


def test_connect_read_only_wal_dataset_leaves_no_sidecar_files(db_path):
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA journal_mode = WAL")
    connection.close()
    before = _directory_contents(db_path.parent)
    assert list(before) == [db_path.name]

    connection = sqlite.connect_read_only(db_path)
    assert connection.execute("SELECT count(*) FROM foo").fetchone()[0] == 2
    assert _directory_contents(db_path.parent) == before
    connection.close()
    assert _directory_contents(db_path.parent) == before


def test_connect_read_only_interrupts_long_query(db_path):
    connection = sqlite.connect_read_only(db_path, timeout=0.2)
    with pytest.raises(sqlite3.OperationalError, match="interrupted"):
        connection.execute("WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) SELECT count(*) FROM c")
    connection.close()
