import logging
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
        op.execute("PRAGMA legacy_alter_table=1;")
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(column)
        op.execute("PRAGMA legacy_alter_table=0;")
    else:
        op.add_column(table_name, column)


def drop_column(table_name, column_name):
    if context.is_offline_mode():
        log.info("Generation of `alter` statements is disabled in offline mode.")
        return
    if _is_sqlite():
        op.execute("PRAGMA legacy_alter_table=1;")
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column(column_name)
        op.execute("PRAGMA legacy_alter_table=0;")
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
