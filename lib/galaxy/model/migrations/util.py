import logging
from abc import (
    ABC,
    abstractmethod,
)
from contextlib import contextmanager
from typing import (
    Any,
    List,
    Optional,
    Sequence,
)

import sqlalchemy as sa
from alembic import (
    context,
    op,
)
from sqlalchemy.exc import OperationalError

log = logging.getLogger(__name__)


class DDLOperation(ABC):
    """Base class for all DDL operations."""

    def run(self) -> Optional[Any]:
        if not self._is_repair_mode():
            return self.execute()
        else:
            if self.pre_execute_check():
                return self.execute()
            else:
                self.log_check_not_passed()
                return None

    @abstractmethod
    def execute(self) -> Optional[Any]: ...

    @abstractmethod
    def pre_execute_check(self) -> bool: ...

    @abstractmethod
    def log_check_not_passed(self) -> None: ...

    def _is_repair_mode(self) -> bool:
        """`--repair` option has been passed to the command."""
        return bool(context.config.get_main_option("repair"))

    def _log_object_exists_message(self, object_name: str) -> None:
        log.info(f"{object_name} already exists. Skipping revision.")

    def _log_object_does_not_exist_message(self, object_name: str) -> None:
        log.info(f"{object_name} does not exist. Skipping revision.")


class DDLAlterOperation(DDLOperation):
    """
    Base class for DDL operations that implement special handling of ALTER statements.
    Ref:
    - https://alembic.sqlalchemy.org/en/latest/ops.html#alembic.operations.Operations.batch_alter_table
    - https://alembic.sqlalchemy.org/en/latest/batch.html
    """

    def __init__(self, table_name: str) -> None:
        self.table_name = table_name

    def run(self) -> Optional[Any]:
        if context.is_offline_mode():
            log.info("Generation of `alter` statements is disabled in offline mode.")
            return None
        return super().run()

    def execute(self) -> Optional[Any]:
        if _is_sqlite():
            with legacy_alter_table(), op.batch_alter_table(self.table_name) as batch_op:
                return self.batch_execute(batch_op)
        else:
            return self.non_batch_execute()  # use regular op context for non-sqlite db

    @abstractmethod
    def batch_execute(self, batch_op) -> Optional[Any]: ...

    @abstractmethod
    def non_batch_execute(self) -> Optional[Any]: ...


class CreateTable(DDLOperation):
    """Wraps alembic's create_table directive."""

    def __init__(self, table_name: str, *columns: sa.schema.SchemaItem) -> None:
        self.table_name = table_name
        self.columns = columns

    def execute(self) -> Optional[sa.Table]:
        return op.create_table(self.table_name, *self.columns)

    def pre_execute_check(self) -> bool:
        return not table_exists(self.table_name, False)

    def log_check_not_passed(self) -> None:
        self._log_object_exists_message(f"{self.table_name} table")


class DropTable(DDLOperation):
    """Wraps alembic's drop_table directive."""

    def __init__(self, table_name: str) -> None:
        self.table_name = table_name

    def execute(self) -> None:
        op.drop_table(self.table_name)

    def pre_execute_check(self) -> bool:
        return table_exists(self.table_name, False)

    def log_check_not_passed(self) -> None:
        self._log_object_does_not_exist_message(f"{self.table_name} table")


class CreateIndex(DDLOperation):
    """Wraps alembic's create_index directive."""

    def __init__(self, index_name: str, table_name: str, columns: Sequence, **kw: Any) -> None:
        self.index_name = index_name
        self.table_name = table_name
        self.columns = columns
        self.kw = kw

    def execute(self) -> None:
        op.create_index(self.index_name, self.table_name, self.columns, **self.kw)

    def pre_execute_check(self) -> bool:
        return not index_exists(self.index_name, self.table_name, False)

    def log_check_not_passed(self) -> None:
        name = _table_object_description(self.index_name, self.table_name)
        self._log_object_exists_message(name)


class DropIndex(DDLOperation):
    """Wraps alembic's drop_index directive."""

    def __init__(self, index_name: str, table_name: str) -> None:
        self.index_name = index_name
        self.table_name = table_name

    def execute(self) -> None:
        op.drop_index(self.index_name, table_name=self.table_name)

    def pre_execute_check(self) -> bool:
        return index_exists(self.index_name, self.table_name, False)

    def log_check_not_passed(self) -> None:
        name = _table_object_description(self.index_name, self.table_name)
        self._log_object_does_not_exist_message(name)


class AddColumn(DDLOperation):
    """Wraps alembic's add_column directive."""

    def __init__(self, table_name: str, column: sa.Column) -> None:
        self.table_name = table_name
        self.column = column

    def execute(self) -> None:
        op.add_column(self.table_name, self.column)

    def pre_execute_check(self) -> bool:
        return not column_exists(self.table_name, self.column.name, False)

    def log_check_not_passed(self) -> None:
        name = _table_object_description(self.column.name, self.table_name)
        self._log_object_exists_message(name)


class DropColumn(DDLAlterOperation):
    """Wraps alembic's drop_column directive."""

    def __init__(self, table_name: str, column_name: str) -> None:
        super().__init__(table_name)
        self.column_name = column_name

    def batch_execute(self, batch_op) -> None:
        batch_op.drop_column(self.column_name)

    def non_batch_execute(self) -> None:
        op.drop_column(self.table_name, self.column_name)

    def pre_execute_check(self) -> bool:
        return column_exists(self.table_name, self.column_name, False)

    def log_check_not_passed(self) -> None:
        name = _table_object_description(self.column_name, self.table_name)
        self._log_object_does_not_exist_message(name)


class AlterColumn(DDLAlterOperation):
    """Wraps alembic's alter_column directive."""

    def __init__(self, table_name: str, column_name: str, **kw: Any) -> None:
        self.table_name = table_name
        self.column_name = column_name
        self.kw = kw

    def batch_execute(self, batch_op) -> None:
        batch_op.alter_column(self.column_name, **self.kw)

    def non_batch_execute(self) -> None:
        op.alter_column(self.table_name, self.column_name, **self.kw)

    def pre_execute_check(self) -> bool:
        # Assume that if a column exists, it can be altered.
        return column_exists(self.table_name, self.column_name, False)

    def log_check_not_passed(self) -> None:
        name = _table_object_description(self.column_name, self.table_name)
        self._log_object_does_not_exist_message(name)


class CreateForeignKey(DDLAlterOperation):
    """Wraps alembic's create_foreign_key directive."""

    def __init__(
        self,
        foreign_key_name: str,
        table_name: str,
        referent_table: str,
        local_cols: List[str],
        remote_cols: List[str],
        **kw: Any,
    ) -> None:
        super().__init__(table_name)
        self.foreign_key_name = foreign_key_name
        self.referent_table = referent_table
        self.local_cols = local_cols
        self.remote_cols = remote_cols
        self.kw = kw

    def batch_execute(self, batch_op) -> None:
        batch_op.create_foreign_key(
            self.foreign_key_name, self.referent_table, self.local_cols, self.remote_cols, **self.kw
        )

    def non_batch_execute(self) -> None:
        op.create_foreign_key(
            self.foreign_key_name, self.table_name, self.referent_table, self.local_cols, self.remote_cols, **self.kw
        )

    def pre_execute_check(self) -> bool:
        return not foreign_key_exists(self.foreign_key_name, self.table_name, False)

    def log_check_not_passed(self) -> None:
        name = _table_object_description(self.foreign_key_name, self.table_name)
        self._log_object_exists_message(name)


class CreateUniqueConstraint(DDLAlterOperation):
    """Wraps alembic's create_unique_constraint directive."""

    def __init__(self, constraint_name: str, table_name: str, columns: List[str]) -> None:
        super().__init__(table_name)
        self.constraint_name = constraint_name
        self.columns = columns

    def batch_execute(self, batch_op) -> None:
        batch_op.create_unique_constraint(self.constraint_name, self.columns)

    def non_batch_execute(self) -> None:
        op.create_unique_constraint(self.constraint_name, self.table_name, self.columns)

    def pre_execute_check(self) -> bool:
        return not unique_constraint_exists(self.constraint_name, self.table_name, False)

    def log_check_not_passed(self) -> None:
        name = _table_object_description(self.constraint_name, self.table_name)
        self._log_object_exists_message(name)


class DropConstraint(DDLAlterOperation):
    """Wraps alembic's drop_constraint directive."""

    def __init__(self, constraint_name: str, table_name: str) -> None:
        super().__init__(table_name)
        self.constraint_name = constraint_name

    def batch_execute(self, batch_op) -> None:
        batch_op.drop_constraint(self.constraint_name)

    def non_batch_execute(self) -> None:
        op.drop_constraint(self.constraint_name, self.table_name)

    def pre_execute_check(self) -> bool:
        return unique_constraint_exists(self.constraint_name, self.table_name, False)

    def log_check_not_passed(self) -> None:
        name = _table_object_description(self.constraint_name, self.table_name)
        self._log_object_does_not_exist_message(name)


def create_table(table_name: str, *columns: sa.schema.SchemaItem) -> Optional[sa.Table]:
    return CreateTable(table_name, *columns).run()


def drop_table(table_name: str) -> None:
    DropTable(table_name).run()


def add_column(table_name: str, column: sa.Column) -> None:
    AddColumn(table_name, column).run()


def drop_column(table_name, column_name) -> None:
    DropColumn(table_name, column_name).run()


def alter_column(table_name: str, column_name: str, **kw) -> None:
    AlterColumn(table_name, column_name, **kw).run()


def create_index(index_name, table_name, columns, **kw) -> None:
    CreateIndex(index_name, table_name, columns, **kw).run()


def drop_index(index_name, table_name) -> None:
    DropIndex(index_name, table_name).run()


def create_foreign_key(
    foreign_key_name: str,
    table_name: str,
    referent_table: str,
    local_cols: List[str],
    remote_cols: List[str],
    **kw: Any,
) -> None:
    CreateForeignKey(foreign_key_name, table_name, referent_table, local_cols, remote_cols, **kw).run()


def create_unique_constraint(constraint_name: str, table_name: str, columns: List[str]) -> None:
    CreateUniqueConstraint(constraint_name, table_name, columns).run()


def drop_constraint(constraint_name: str, table_name: str) -> None:
    DropConstraint(constraint_name, table_name).run()


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


def foreign_key_exists(constraint_name: str, table_name: str, default: bool) -> bool:
    """Check if unique constraint exists. If running in offline mode, return default."""
    if context.is_offline_mode():
        _log_offline_mode_message(foreign_key_exists.__name__, default)
        return default
    constraints = _inspector().get_foreign_keys(table_name)
    return any(c["name"] == constraint_name for c in constraints)


def unique_constraint_exists(constraint_name: str, table_name: str, default: bool) -> bool:
    """Check if unique constraint exists. If running in offline mode, return default."""
    if context.is_offline_mode():
        _log_offline_mode_message(unique_constraint_exists.__name__, default)
        return default
    constraints = _inspector().get_unique_constraints(table_name)
    return any(c["name"] == constraint_name for c in constraints)


def _table_object_description(object_name: str, table_name: str) -> str:
    return f"{object_name} on {table_name} table"


def _log_offline_mode_message(function_name: str, return_value: Any) -> None:
    log.info(
        f"This script is being executed in offline mode, so it cannot connect to the database. "
        f"Therefore, function `{function_name}` will return the value `{return_value}`, "
        f"which is the expected value during normal operation."
    )


def _inspector() -> Any:
    bind = op.get_context().bind
    return sa.inspect(bind)


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
