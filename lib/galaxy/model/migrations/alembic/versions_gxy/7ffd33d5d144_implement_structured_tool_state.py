"""implement structured tool state

Revision ID: 7ffd33d5d144
Revises: 25b092f7938b
Create Date: 2022-11-09 15:53:11.451185

"""

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
)

from galaxy.model.custom_types import (
    JSONType,
    UUIDType,
)
from galaxy.model.database_object_names import build_index_name
from galaxy.model.migrations.util import (
    add_column,
    create_foreign_key,
    create_index,
    create_table,
    drop_column,
    drop_index,
    drop_table,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "7ffd33d5d144"
down_revision = "25b092f7938b"
branch_labels = None
depends_on = None

job_table_name = "job"
tool_source_table_name = "tool_source"
tool_request_table_name = "tool_request"
request_column_name = "tool_request_id"
job_request_index_name = build_index_name(job_table_name, request_column_name)
workflow_request_to_input_dataset_table_name = "workflow_request_to_input_dataset"
workflow_request_to_input_collection_table_name = "workflow_request_to_input_collection_dataset"
workflow_request_to_input_parameter_table_name = "workflow_request_input_step_parameter"
workflow_input_request_column_name = "request"
workflow_landing_request_table_name = "workflow_landing_request"
tool_landing_request_table_name = "tool_landing_request"


def upgrade():
    with transaction():
        create_table(
            tool_landing_request_table_name,
            Column("id", Integer, primary_key=True),
            Column("user_id", Integer, index=True, nullable=True),
            Column("create_time", DateTime),
            Column("update_time", DateTime, nullable=True),
            Column("request_state", JSONType),
            Column("client_secret", String(255), nullable=True),
            Column("uuid", UUIDType, nullable=False, index=True),
        )

        create_table(
            workflow_landing_request_table_name,
            Column("id", Integer, primary_key=True),
            Column("user_id", Integer, index=True, nullable=True),
            Column("stored_workflow_id", Integer, index=True),
            Column("workflow_id", Integer, index=True),
            Column("create_time", DateTime),
            Column("update_time", DateTime, nullable=True),
            Column("request_state", JSONType),
            Column("client_secret", String(255), nullable=True),
            Column("uuid", UUIDType, nullable=False, index=True),
        )

        create_foreign_key(
            "foreign_key_user_id",
            tool_landing_request_table_name,
            "galaxy_user",
            ["user_id"],
            ["id"],
        )
        create_foreign_key(
            "foreign_key_user_id",
            workflow_landing_request_table_name,
            "galaxy_user",
            ["user_id"],
            ["id"],
        )
        create_foreign_key(
            "foreign_key_stored_workflow_id",
            workflow_landing_request_table_name,
            "stored_workflow",
            ["stored_workflow_id"],
            ["id"],
        )
        create_foreign_key(
            "foreign_key_workflow_id",
            workflow_landing_request_table_name,
            "workflow",
            ["workflow_id"],
            ["id"],
        )

        create_table(
            tool_source_table_name,
            Column("id", Integer, primary_key=True),
            Column("hash", String(255), index=True),
            Column("source", JSONType),
        )
        create_table(
            tool_request_table_name,
            Column("id", Integer, primary_key=True),
            Column("request", JSONType),
            Column("state", String(32)),
            Column("state_message", JSONType),
            Column("tool_source_id", Integer, index=True),
            Column("history_id", Integer, index=True),
        )

        create_foreign_key(
            "foreign_key_tool_source_id",
            tool_request_table_name,
            tool_source_table_name,
            ["tool_source_id"],
            ["id"],
        )

        create_foreign_key(
            "foreign_key_history_id",
            tool_request_table_name,
            "history",
            ["history_id"],
            ["id"],
        )

        add_column(
            job_table_name,
            Column(request_column_name, Integer, default=None),
        )

        create_foreign_key(
            "foreign_key_tool_request_id",
            job_table_name,
            tool_request_table_name,
            ["tool_request_id"],
            ["id"],
        )

        create_index(job_request_index_name, job_table_name, [request_column_name])

        add_column(
            workflow_request_to_input_dataset_table_name,
            Column(workflow_input_request_column_name, JSONType, default=None),
        )
        add_column(
            workflow_request_to_input_collection_table_name,
            Column(workflow_input_request_column_name, JSONType, default=None),
        )
        add_column(
            workflow_request_to_input_parameter_table_name,
            Column(workflow_input_request_column_name, JSONType, default=None),
        )


def downgrade():
    with transaction():
        drop_column(workflow_request_to_input_dataset_table_name, workflow_input_request_column_name)
        drop_column(workflow_request_to_input_collection_table_name, workflow_input_request_column_name)
        drop_column(workflow_request_to_input_parameter_table_name, workflow_input_request_column_name)
        drop_index(job_request_index_name, job_table_name)
        drop_column(job_table_name, request_column_name)
        drop_table(tool_request_table_name)
        drop_table(tool_source_table_name)

        drop_table(tool_landing_request_table_name)
        drop_table(workflow_landing_request_table_name)
