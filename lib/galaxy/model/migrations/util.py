import logging

from alembic import (
    context,
    op,
)
from sqlalchemy import inspect

log = logging.getLogger(__name__)


def drop_column(table_name, column_name):
    if context.is_offline_mode():
        return _handle_offline_mode(f"drop_column({table_name}, {column_name})", None)

    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_column(column_name)


def create_index(index_name, table_name, columns):
    if index_exists(index_name, table_name):
        msg = f"Index with name {index_name} on {table_name} already exists. Skipping revision."
        log.info(msg)
    else:
        op.create_index(index_name, table_name, columns)


def drop_index(index_name, table_name) -> None:
    if index_exists(index_name, table_name):
        op.drop_index(index_name, table_name=table_name)


def column_exists(table_name, column_name):
    if context.is_offline_mode():
        return _handle_offline_mode(f"column_exists({table_name}, {column_name})")

    bind = op.get_context().bind
    insp = inspect(bind)
    columns = insp.get_columns(table_name)
    return any(c["name"] == column_name for c in columns)


def index_exists(index_name, table_name):
    if context.is_offline_mode():
        return _handle_offline_mode(f"index_exists({index_name}, {table_name})")

    bind = op.get_context().bind
    insp = inspect(bind)
    indexes = insp.get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def _handle_offline_mode(code, return_value=False):
    msg = (
        "This script is being executed in offline mode and cannot connect to the database. "
        f"Therefore, `{code}` returns `{return_value}` by default."
    )
    log.info(msg)
    return return_value
