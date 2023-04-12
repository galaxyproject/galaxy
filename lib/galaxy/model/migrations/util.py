import logging
from contextlib import contextmanager
from typing import (
    Any,
    List,
    Optional,
)

import sqlalchemy as sa
from alembic import (
    context,
    op,
)
from sqlalchemy.exc import OperationalError

log = logging.getLogger(__name__)


def create_table(table_name: str, *columns: sa.schema.SchemaItem, **kw: Any) -> Optional[sa.Table]:
    return op.create_table(table_name, *columns, **kw)


def drop_table(table_name: str) -> None:
    op.drop_table(table_name)


def add_column(table_name: str, column: sa.Column) -> None:
    if context.is_offline_mode():
        log.info("Generation of `alter` statements is disabled in offline mode.")
        return
    if _is_sqlite():
        with legacy_alter_table(), op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(column)
    else:
        op.add_column(table_name, column)


def drop_column(table_name, column_name):
    if context.is_offline_mode():
        log.info("Generation of `alter` statements is disabled in offline mode.")
        return
    if _is_sqlite():
        with legacy_alter_table(), op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column(column_name)
    else:
        op.drop_column(table_name, column_name)


def create_index(index_name, table_name, columns, **kw):
    op.create_index(index_name, table_name, columns, **kw)


def drop_index(index_name, table_name):
    op.drop_index(index_name, table_name)


def add_unique_constraint(index_name: str, table_name: str, columns: List[str]):
    if _is_sqlite():
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.create_unique_constraint(index_name, columns)
    else:
        op.create_unique_constraint(index_name, table_name, columns)


def drop_unique_constraint(index_name: str, table_name: str):
    if _is_sqlite():
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(index_name)
    else:
        op.drop_constraint(index_name, table_name)


def _is_sqlite() -> bool:
    bind = op.get_context().bind
    return bool(bind and bind.engine.name == "sqlite")


@contextmanager
def legacy_alter_table():
    """
    Wrapper required for add/drop column statements.
    Prevents error when column belongs to a table referenced in a view. Relevant to sqlite only.
    Ref: https://github.com/sqlalchemy/alembic/issues/1207
    Ref: https://sqlite.org/pragma.html#pragma_legacy_alter_table
    """
    try:
        op.execute("PRAGMA legacy_alter_table=1;")
        yield
    finally:
        op.execute("PRAGMA legacy_alter_table=0;")


@contextmanager
def transaction():
    """
    Wraps multiple statements in upgrade/downgrade revision script functions in
    a database transaction, ensuring transactional control.

    Used for SQLite only. Although SQLite supports transactional DDL, pysqlite does not.
    Ref: https://bugs.python.org/issue10740
    """
    if not _is_sqlite():
        yield  # For postgresql, alembic ensures transactional context.
    else:
        try:
            op.execute("BEGIN")
            yield
            op.execute("END")
        except OperationalError:
            op.execute("ROLLBACK")
            raise
