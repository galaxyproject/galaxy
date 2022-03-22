import logging
from contextlib import contextmanager

from alembic import op
from sqlalchemy.exc import (
    OperationalError,
    ProgrammingError,
)

log = logging.getLogger(__name__)


def drop_column(table, column):
    with op.batch_alter_table(table) as batch_op:
        batch_op.drop_column(column)


@contextmanager
def ignore_add_column_error(table, column):
    """
    Use this context manager to wrap statements in upgrade/downgrade functions
    in revision files when a statement may cause an error that may be safely
    ignored. For example, in revision b182f655505f, if an upgrade operation is
    executed on a database that has been previoiusly upgraded via SQLAlchemy
    Migrate to version 181, a subsequent upgrade to Alembic may cause such as
    error. For more details, see https://github.com/galaxyproject/galaxy/issues/13528.

    We are checking for 2 different error types: OperationalError is raised
    for SQLite, ProgrammingError is raised for PostgreSQL.
    """
    statement = f"ALTER TABLE {table} ADD COLUMN {column}"
    try:
        yield
    except (ProgrammingError, OperationalError) as e:
        if e.statement.startswith(statement):
            log.error(f"Ignoring error: {e}")
        else:
            raise e
