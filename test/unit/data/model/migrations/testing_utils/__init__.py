from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.sql.compiler import IdentifierPreparer

from galaxy.model.database_utils import create_database
from ...testing_utils import DbUrl


@contextmanager
def create_and_drop_database(url: DbUrl) -> Iterator[None]:
    """
    Context manager that creates a database. If the database is postgresql, it is dropped on exit;
    a sqlite database should be removed automatically by tempfile.
    """
    try:
        create_database(url)
        yield
    finally:
        if _is_postgres(url):
            _drop_postgres_database(url)


@contextmanager
def drop_database(url: DbUrl) -> Iterator[None]:
    """
    Context manager that ensures a postgres database identified by url is dropped on exit;
    a sqlite database should be removed automatically by tempfile.
    """
    try:
        yield
    finally:
        if _is_postgres(url):
            _drop_postgres_database(url)


def _is_postgres(url: DbUrl) -> bool:
    return url.startswith("postgres")


def _drop_postgres_database(url: DbUrl) -> None:
    db_url = make_url(url)
    database = db_url.database
    connection_url = db_url.set(database="postgres")
    engine = create_engine(connection_url, isolation_level="AUTOCOMMIT")
    preparer = IdentifierPreparer(engine.dialect)
    database = preparer.quote(database)
    stmt = f"DROP DATABASE IF EXISTS {database}"
    with engine.connect() as conn:
        conn.execute(stmt)
    engine.dispose()
