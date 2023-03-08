"""
Utility functions for use in revision scripts.
"""
import logging
from typing import (
    Any,
    Optional,
    Sequence,
)

import sqlalchemy as sa
from alembic import (
    context,
    op,
)

log = logging.getLogger(__name__)


def create_table(table_name: str, *columns: sa.schema.SchemaItem, **kw: Any) -> Optional[sa.Table]:
    """Create table if not exists. Return Table object if created."""
    if not table_exists(table_name, False):
        return op.create_table(table_name, *columns, **kw)
    else:
        _log_object_exists_message(table_name)
        return None


def drop_table(table_name: str) -> None:
    """Drop table if exists."""
    if table_exists(table_name, True):
        op.drop_table(table_name)
    else:
        _log_object_does_not_exist_message(table_name)


def table_exists(table_name: str, default: bool) -> bool:
    """Check if table exists. If running in offline mode, return default."""
    if context.is_offline_mode():
        _log_offline_mode_message(table_exists.__name__, default)
        return default
    return _inspector().has_table(table_name)


def add_column(table_name: str, column: sa.Column) -> None:
    """
    Add column to table if not exists.

    Use Alembic's batch operations to handle limitations of SQLite.
    """
    if context.is_offline_mode():
        log.info("Generation of `alter` statements is disabled in offline mode.")
        return

    if not column_exists(table_name, column.name, False):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(column)
    else:
        name = _column_name(column.name, table_name)
        return _log_object_exists_message(name)


def drop_column(table_name: str, column_name: str) -> None:
    """
    Drop column if exists.

    Use Alembic's batch operations to handle limitations of SQLite.
    """
    if context.is_offline_mode():
        log.info("Generation of `alter` statements is disabled in offline mode.")
        return

    if column_exists(table_name, column_name, True):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column(column_name)
    else:
        name = _column_name(column_name, table_name)
        _log_object_does_not_exist_message(name)


def column_exists(table_name: str, column_name: str, default: bool) -> bool:
    """Check if column exists. If running in offline mode, return default."""
    if context.is_offline_mode():
        _log_offline_mode_message(column_exists.__name__, default)
        return default
    columns = _inspector().get_columns(table_name)
    return any(c["name"] == column_name for c in columns)


def create_index(index_name: str, table_name: str, columns: Sequence) -> None:
    """Create index if not exists."""
    if not index_exists(index_name, table_name, False):
        op.create_index(index_name, table_name, columns)
    else:
        name = _index_name(index_name, table_name)
        _log_object_exists_message(name)


def drop_index(index_name: str, table_name: str) -> None:
    """Drop index if exists."""
    if index_exists(index_name, table_name, True):
        op.drop_index(index_name, table_name)
    else:
        name = _index_name(index_name, table_name)
        _log_object_does_not_exist_message(name)


def index_exists(index_name: str, table_name: str, default: bool) -> bool:
    """Check if index exists. If running in offline mode, return default."""
    if context.is_offline_mode():
        _log_offline_mode_message(index_exists.__name__, default)
        return default
    indexes = _inspector().get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def _log_offline_mode_message(function_name: str, return_value: Any) -> None:
    log.info(
        f"This script is being executed in offline mode, so it cannot connect to the database. "
        f"Therefore, function `{function_name}` will return the value `{return_value}`, "
        f"which is the expected value during normal operation."
    )


def _log_object_exists_message(object_name: str) -> None:
    log.info(f"{object_name} already exists. Skipping revision.")


def _log_object_does_not_exist_message(object_name: str) -> None:
    log.info(f"{object_name} does not exist. Skipping revision.")


def _column_name(column_name: str, table_name: str) -> str:
    return f"{column_name} on {table_name} table"


def _index_name(index_name: str, table_name: str) -> str:
    return f"{index_name} on {table_name} table"


def _inspector():
    bind = op.get_context().bind
    return sa.inspect(bind)
