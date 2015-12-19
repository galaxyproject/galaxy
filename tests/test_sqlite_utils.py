from galaxy.util import sqlite


def test_query_whitelisting():
    __assert_whitelisted("SELECT * from FOO")
    __assert_whitelisted("SELECT f.col1, f.col2 from FOO as f")
    __assert_whitelisted("SELECT f.col1, b.col2 from FOO as f inner join BAR as b on f.id = b.foo_id")
    __assert_not_whitelisted("UPDATE FOO SET foo=6")
    __assert_not_whitelisted("TRUNCATE FOO")


def test_sqlite_exploits():
    # This is not really testing any Galaxy code, just experimenting with ways
    # to attempt to exploit sqlite3 connections.

    # More info...
    # http://atta.cked.me/home/sqlite3injectioncheatsheet

    connection = sqlite.connect(":memory:")
    connection.execute("create TABLE FOO (foo1 text)")
    __assert_has_n_rows(connection, "select * from FOO", 0)
    __assert_query_errors(connection, "select * from FOOX")

    # Make sure sqlite query cannot execute multiple statements
    __assert_query_errors(connection, "select * from FOO; select * from FOO")

    # Make sure sqlite cannot select on PRAGMA results
    __assert_query_errors(connection, "select * from (PRAGMA database_list)")

    __assert_has_n_rows(connection, "select * from FOO where foo1 in (SELECT foo1 from FOO)", 0)
    # Ensure nested queries cannot modify database.
    __assert_query_errors(connection, "select * from FOO where foo1 in (INSERT INTO FOO VALUES ('bar')")

    # Should access to the schema be blacklisted?
    # __assert_has_n_rows(connection, "select * from SQLITE_MASTER", 0)


def __assert_has_n_rows(connection, query, n):
    count = 0
    for row in connection.cursor().execute(query):
        count += 1
    assert count == n


def __assert_query_errors(connection, query):
    exception = False
    try:
        for row in connection.cursor().execute(query):
            pass
    except Exception:
        exception = True
    assert exception


def __assert_whitelisted( query ):
    assert sqlite.is_read_only_query(query), "Query [%s] fails whitelist." % query


def __assert_not_whitelisted( query ):
    assert not sqlite.is_read_only_query(query), "Query [%s] incorrectly fails whitelist." % query
