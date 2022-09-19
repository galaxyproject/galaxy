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


def column_exists(table_name, column_name):
    if context.is_offline_mode():
        return _handle_offline_mode(f"column_exists({table_name}, {column_name})", False)

    bind = op.get_context().bind
    insp = inspect(bind)
    columns = insp.get_columns(table_name)
    return any(c["name"] == column_name for c in columns)


def _handle_offline_mode(code, return_value):
    msg = (
        "This script is being executed in offline mode and cannot connect to the database. "
        f"Therefore, `{code}` returns `{return_value}` by default."
    )
    log.info(msg)
    return return_value
