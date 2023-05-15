"""
Naming convention and helper functions for generating names of database
constraints and indexes.
"""

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


def foreign_key(table_name, column_name):
    return f"{table_name}_{column_name}_fkey"


def unique_constraint(table_name, column_name):
    return f"{table_name}_{column_name}_key"


def check_constraint(table_name, column_name):
    return f"{table_name}_{column_name}_check"


def index(table_name, column_name):
    return f"ix_{table_name}_{column_name}"
