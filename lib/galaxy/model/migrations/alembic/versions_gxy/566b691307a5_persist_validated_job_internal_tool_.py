"""Persist validated job internal tool state and enforce tool request constraints.

Revision ID: 566b691307a5
Revises: 9930b68c85af
Create Date: 2025-09-30 04:48:19.727414

"""

from sqlalchemy import (
    Column,
    Integer,
    String,
)

from galaxy.model.custom_types import JSONType
from galaxy.model.migrations.util import (
    add_column,
    alter_column,
    drop_column,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "566b691307a5"
down_revision = "9930b68c85af"
branch_labels = None
depends_on = None

table_name = "job"
column_name = "tool_state"

# additional database object names used in this revision
tool_request_table_name = "tool_request"
tool_request_history_id_column = "history_id"

tool_source_table_name = "tool_source"
tool_source_source_class_column = "source_class"


def upgrade():
    # Wrap statements for sqlite safety and to ensure atomicity where supported
    with transaction():
        # Persist validated job internal tool state
        add_column(table_name, Column(column_name, JSONType))

        # Ensure tool_request.history_id is NOT NULL
        alter_column(
            tool_request_table_name,
            tool_request_history_id_column,
            existing_type=Integer(),
            nullable=False,
        )

        # Add tool_source.source_class as a new NOT NULL string column
        add_column(
            tool_source_table_name,
            Column(tool_source_source_class_column, String(255), nullable=False),
        )


def downgrade():
    # Reverse operations in a transaction
    with transaction():
        # Drop tool_source.source_class
        drop_column(tool_source_table_name, tool_source_source_class_column)

        # Revert tool_request.history_id to be nullable
        alter_column(
            tool_request_table_name,
            tool_request_history_id_column,
            existing_type=Integer(),
            nullable=True,
        )

        # Drop job.tool_state
        drop_column(table_name, column_name)
