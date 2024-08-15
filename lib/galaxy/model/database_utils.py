import sqlite3
from contextlib import contextmanager
from typing import (
    NewType,
    Optional,
)

from sqlalchemy import (
    create_engine,
    select,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import object_session
from sqlalchemy.sql.compiler import IdentifierPreparer
from sqlalchemy.sql.expression import (
    Executable,
    text,
)

from galaxy.exceptions import ConfigurationError
from galaxy.model import Job

DbUrl = NewType("DbUrl", str)


def database_exists(db_url, database=None):
    """Check if database exists; connect with db_url.

    If database is None, use the database name from db_url.
    """
    dbm = DatabaseManager.make_manager(db_url, database)
    return dbm.exists()


def create_database(db_url, database=None, encoding="utf8", template=None):
    """Create database; connect with db_url.

    If database is None, use the database name from db_url.
    """
    dbm = DatabaseManager.make_manager(db_url, database)
    dbm.create(encoding, template)


@contextmanager
def sqlalchemy_engine(url):
    engine = create_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()


class DatabaseManager:
    @staticmethod
    def make_manager(db_url, database):
        if db_url.startswith("postgres"):
            return PosgresDatabaseManager(db_url, database)
        elif db_url.startswith("sqlite"):
            return SqliteDatabaseManager(db_url, database)
        elif db_url.startswith("mysql"):
            return MySQLDatabaseManager(db_url, database)
        else:
            raise ConfigurationError(f"Invalid database URL: {db_url}")

    def __init__(self, db_url, database):
        self.url = make_url(db_url)
        self.database = database
        if not database:
            self._handle_no_database()


class PosgresDatabaseManager(DatabaseManager):
    def _handle_no_database(self):
        self.database = self.url.database  # use database from db_url
        self.url = self.url.set(database="postgres")

    def exists(self):
        with sqlalchemy_engine(self.url) as engine:
            stmt = text("SELECT 1 FROM pg_database WHERE datname=:database")
            stmt = stmt.bindparams(database=self.database)
            with engine.connect() as conn:
                return bool(conn.scalar(stmt))

    def create(self, encoding, template):
        with sqlalchemy_engine(self.url) as engine:
            preparer = IdentifierPreparer(engine.dialect)
            template = template or "template1"
            database, template = preparer.quote(self.database), preparer.quote(template)
            stmt = text(f"CREATE DATABASE {database} ENCODING '{encoding}' TEMPLATE {template}")
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(stmt)


class SqliteDatabaseManager(DatabaseManager):
    def _handle_no_database(self):
        self.database = self.url.database  # use database from db_url

    def exists(self):
        def can_connect_to_dbfile():
            try:
                sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            except sqlite3.OperationalError:
                return False
            else:
                return True

        db = self.url.database
        # No database or ':memory:' creates an in-memory database
        return not db or db == ":memory:" or can_connect_to_dbfile()

    def create(self, *args):
        # Ignore any args (encoding, template)
        sqlite3.connect(f"file:{self.url.database}", uri=True)


class MySQLDatabaseManager(DatabaseManager):
    def _handle_no_database(self):
        self.database = self.url.database  # use database from db_url

    def exists(self):
        with sqlalchemy_engine(self.url) as engine:
            stmt = text("SELECT schema_name FROM information_schema.schemata WHERE schema_name=:database")
            stmt = stmt.bindparams(database=self.database)
            with engine.connect() as conn:
                return bool(conn.scalar(stmt))

    def create(self, encoding, *arg):
        # Ignore any args (template)
        with sqlalchemy_engine(self.url) as engine:
            preparer = IdentifierPreparer(engine.dialect)
            database = preparer.quote(self.database)
            stmt = text(f"CREATE DATABASE {database} CHARACTER SET = '{encoding}'")
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(stmt)


def is_one_database(db1_url: str, db2_url: Optional[str]):
    """
    Check if the arguments refer to one database. This will be true
    if only one argument is passed, or if the urls are the same.
    URLs are strings, so sameness is determined via string comparison.
    """
    # TODO: Consider more aggressive check here that this is not the same
    # database file under the hood.
    return not (db1_url and db2_url and db1_url != db2_url)


def supports_returning(engine: Engine) -> bool:
    """
    Return True if the database bound to `engine` supports the `RETURNING` SQL clause.
    """
    stmt = update(Job).where(Job.id == -1).values(create_time=None).returning(Job.id)
    return _statement_executed_without_error(stmt, engine)


def supports_skip_locked(engine: Engine) -> bool:
    """
    Return True if the database bound to `engine` supports the `SKIP_LOCKED` parameter.
    """
    stmt = select(Job).where(Job.id == -1).with_for_update(skip_locked=True)
    return _statement_executed_without_error(stmt, engine)


def _statement_executed_without_error(statement: Executable, engine: Engine) -> bool:
    # Execute statement against database, then issue a rollback.
    try:
        with engine.connect() as conn, conn.begin() as trans:
            conn.execute(statement)
            trans.rollback()  # ensure no changes to database
            return True
    except Exception:
        return False


def is_postgres(url: DbUrl) -> bool:
    return url.startswith("postgres")


def ensure_object_added_to_session(object_to_add, *, object_in_session=None, session=None) -> bool:
    """
    This function is intended as a safeguard to mimic pre-SQLAlchemy 2.0 behavior.
    `object_to_add` was implicitly merged into a Session prior to SQLAlchemy 2.0, which was indicated
    by `RemovedIn20Warning` warnings logged while running Galaxy's tests. (See https://github.com/galaxyproject/galaxy/issues/12541)
    As part of the upgrade to 2.0, the `cascade_backrefs=False` argument was added to the relevant relationships that turned off this behavior.
    This function is called from the code that triggered these warnings, thus emulating the cascading behavior.
    The intention is to remove all such calls, as well as this function definition, after the move to SQLAlchemy 2.0.
    # Ref: https://docs.sqlalchemy.org/en/14/changelog/migration_14.html#cascade-backrefs-behavior-deprecated-for-removal-in-2-0
    """
    if session:
        session.add(object_to_add)
        return True
    if object_in_session and object_session(object_in_session):
        object_session(object_in_session).add(object_to_add)  # type:ignore[union-attr]
        return True
    return False
