import sqlite3
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.sql.compiler import IdentifierPreparer
from sqlalchemy.sql.expression import text

from galaxy.exceptions import ConfigurationError


def database_exists(db_url, database=None):
    """Check if database exists; connect with db_url.

    If database is None, use the database name from db_url.
    """
    dbm = DatabaseManager.make_manager(db_url, database)
    return dbm.exists()


def create_database(db_url, database=None, encoding='utf8', template=None):
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
        if db_url.startswith('postgresql'):
            return PosgresDatabaseManager(db_url, database)
        elif db_url.startswith('sqlite'):
            return SqliteDatabaseManager(db_url, database)
        else:
            raise ConfigurationError(f'Invalid database URL: {db_url}')

    def __init__(self, db_url, database):
        self.url = make_url(db_url)
        self.database = database
        if not database:
            self._handle_no_database()


class PosgresDatabaseManager(DatabaseManager):

    def _handle_no_database(self):
        self.database = self.url.database  # use database from db_url
        self.url.database = 'postgres'

    def exists(self):
        with sqlalchemy_engine(self.url) as engine:
            stmt = text('SELECT 1 FROM pg_database WHERE datname=:database')
            stmt = stmt.bindparams(database=self.database)
            with engine.connect() as conn:
                return bool(conn.scalar(stmt))

    def create(self, encoding, template):
        with sqlalchemy_engine(self.url) as engine:
            preparer = IdentifierPreparer(engine.dialect)
            template = template or 'template1'
            database, template = preparer.quote(self.database), preparer.quote(template)
            stmt = f"CREATE DATABASE {database} ENCODING '{encoding}' TEMPLATE {template}"
            with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
                conn.execute(stmt)


class SqliteDatabaseManager(DatabaseManager):

    def _handle_no_database(self):
        self.database = self.url.database  # use database from db_url

    def exists(self):
        try:
            sqlite3.connect(f'file:{self.url.database}?mode=ro', uri=True)
        except sqlite3.OperationalError:
            return False
        else:
            return True

    def create(self, encoding, template):
        # Don't use encoding and template for sqlite
        sqlite3.connect(f'file:{self.url.database}', uri=True)
