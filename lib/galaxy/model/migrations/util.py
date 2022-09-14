import logging

from alembic import (
    context,
    op,
)
from sqlalchemy import inspect

log = logging.getLogger(__name__)


def drop_column(table_name, column_name):
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_column(column_name)


def column_exists(table_name, column_name):
    if is_offline_mode():
        msg = (
            "This script is being executed in offline mode and cannot connect to the database. "
            f"Therefore, `column_exists({table_name}, {column_name})` returns `False` by default."
        )
        log.debug(msg)
        return False
    bind = op.get_context().bind
    insp = inspect(bind)
    columns = insp.get_columns(table_name)
    return any(c["name"] == column_name for c in columns)


def is_offline_mode():
    cmd_opts = context.config.cmd_opts
    return cmd_opts and cmd_opts.sql
