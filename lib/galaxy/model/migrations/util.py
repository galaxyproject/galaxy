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
    if not _is_repair_mode():
        return op.create_table(table_name, *columns, **kw)
    else:
        if not table_exists(table_name, False):
            return op.create_table(table_name, *columns, **kw)
        else:
            _log_object_exists_message(table_name)
            return None


def drop_table(table_name: str) -> None:
    if not _is_repair_mode():
        op.drop_table(table_name)
    else:
        if table_exists(table_name, True):
            op.drop_table(table_name)
        else:
            _log_object_does_not_exist_message(table_name)


def add_column(table_name: str, column: sa.Column) -> None:
    if context.is_offline_mode():
        log.info("Generation of `alter` statements is disabled in offline mode.")
        return

    if not _is_repair_mode():
        op.add_column(table_name, column)
    else:
        if not column_exists(table_name, column.name, False):
            op.add_column(table_name, column)
        else:
            name = _column_name(column.name, table_name)
            _log_object_exists_message(name)


def drop_column(table_name, column_name):
    def execute():
        if _is_sqlite():
            with legacy_alter_table(), op.batch_alter_table(table_name) as batch_op:
                batch_op.drop_column(column_name)
        else:
            op.drop_column(table_name, column_name)

    if context.is_offline_mode():
        log.info("Generation of `alter` statements is disabled in offline mode.")
        return

    if not _is_repair_mode():
        execute()
    else:
        if column_exists(table_name, column_name, False):
            execute()
        else:
            name = _column_name(column_name, table_name)
            _log_object_does_not_exist_message(name)


def create_index(index_name, table_name, columns, **kw):
    if not _is_repair_mode():
        op.create_index(index_name, table_name, columns, **kw)
    else:
        if not index_exists(index_name, table_name, False):
            op.create_index(index_name, table_name, columns)
        else:
            name = _index_name(index_name, table_name)
            _log_object_exists_message(name)


def drop_index(index_name, table_name):
    if not _is_repair_mode():
        op.drop_index(index_name, table_name)
    else:
        if index_exists(index_name, table_name, True):
            op.drop_index(index_name, table_name)
        else:
            name = _index_name(index_name, table_name)
            _log_object_does_not_exist_message(name)


def add_unique_constraint(index_name: str, table_name: str, columns: List[str]):
    def execute():
        if _is_sqlite():
            with op.batch_alter_table(table_name) as batch_op:
                batch_op.create_unique_constraint(index_name, columns)
        else:
            op.create_unique_constraint(index_name, table_name, columns)

    if not _is_repair_mode():
        execute()
    else:
        if not unique_constraint_exists(index_name, table_name, False):
            execute()
        else:
            name = _constraint_name(index_name, table_name)
            _log_object_does_not_exist_message(name)


def drop_unique_constraint(index_name: str, table_name: str):
    def execute():
        if _is_sqlite():
            with op.batch_alter_table(table_name) as batch_op:
                batch_op.drop_constraint(index_name)
        else:
            op.drop_constraint(index_name, table_name)

    if not _is_repair_mode():
        execute()
    else:
        if unique_constraint_exists(index_name, table_name, False):
            execute()
        else:
            name = _constraint_name(index_name, table_name)
            _log_object_exists_message(name)


def table_exists(table_name: str, default: bool) -> bool:
    """Check if table exists. If running in offline mode, return default."""
    if context.is_offline_mode():
        _log_offline_mode_message(table_exists.__name__, default)
        return default
    return _inspector().has_table(table_name)


def column_exists(table_name: str, column_name: str, default: bool) -> bool:
    """Check if column exists. If running in offline mode, return default."""
    if context.is_offline_mode():
        _log_offline_mode_message(column_exists.__name__, default)
        return default
    columns = _inspector().get_columns(table_name)
    return any(c["name"] == column_name for c in columns)


def index_exists(index_name: str, table_name: str, default: bool) -> bool:
    """Check if index exists. If running in offline mode, return default."""
    if context.is_offline_mode():
        _log_offline_mode_message(index_exists.__name__, default)
        return default
    indexes = _inspector().get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def unique_constraint_exists(constraint_name: str, table_name: str, default: bool) -> bool:
    """Check if unique constraint exists. If running in offline mode, return default."""
    if context.is_offline_mode():
        _log_offline_mode_message(index_exists.__name__, default)
        return default
    constraints = _inspector().get_unique_constraints(table_name)
    return any(c["name"] == constraint_name for c in constraints)


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


def _constraint_name(constraint_name: str, table_name: str) -> str:
    return f"{constraint_name} on {table_name} table"


def _inspector():
    bind = op.get_context().bind
    return sa.inspect(bind)


def _is_sqlite() -> bool:
    bind = op.get_context().bind
    return bool(bind and bind.engine.name == "sqlite")


def _is_repair_mode():
    """`--repair` option has been passed to the command."""
    return bool(context.config.get_main_option("repair"))


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
