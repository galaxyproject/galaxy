"""
Naming convention and helper functions for generating names of database
constraints and indexes.
"""

from typing import (
    List,
    Union,
)

from galaxy.util import listify

# Naming convention applied to database constraints and indexes.
# All except "ix" are conventions used by PostgreSQL by default.
# We keep the "ix" template consistent with historical Galaxy usage.
NAMING_CONVENTION = {
    "pk": "%(table_name)s_pkey",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(column_0_name)s_check",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
}


def build_foreign_key_name(table_name: str, column_names: Union[str, List]) -> str:
    columns = _as_str(column_names)
    return f"{table_name}_{columns}_fkey"


def build_unique_constraint_name(table_name: str, column_names: Union[str, List]) -> str:
    columns = _as_str(column_names)
    return f"{table_name}_{columns}_key"


def build_check_constraint_name(table_name: str, column_name: str) -> str:
    return f"{table_name}_{column_name}_check"


def build_index_name(table_name: str, column_names: Union[str, List]) -> str:
    columns = _as_str(column_names)
    return f"ix_{table_name}_{columns}"


def _as_str(column_names: Union[str, List]) -> str:
    return "_".join(listify(column_names))
