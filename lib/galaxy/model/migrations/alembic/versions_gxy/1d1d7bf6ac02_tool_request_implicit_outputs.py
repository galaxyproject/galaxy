"""Track tool request implicit output collections.

Revision ID: 1d1d7bf6ac02
Revises: 75348cfb3715
Create Date: 2024-11-18 15:39:42.900327

"""

from sqlalchemy import (
    Column,
    Integer,
    String,
)

from galaxy.model.migrations.util import (
    create_foreign_key,
    create_table,
    drop_table,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "1d1d7bf6ac02"
down_revision = "75348cfb3715"
branch_labels = None
depends_on = None

association_table_name = "tool_request_implicit_collection_association"


def upgrade():
    with transaction():
        create_table(
            association_table_name,
            Column("id", Integer, primary_key=True),
            Column("tool_request_id", Integer, index=True),
            Column("dataset_collection_id", Integer, index=True),
            Column("output_name", String(255), nullable=False),
        )

        create_foreign_key(
            "fk_trica_tri",
            association_table_name,
            "tool_request",
            ["tool_request_id"],
            ["id"],
        )

        create_foreign_key(
            "fk_trica_dci",
            association_table_name,
            "history_dataset_collection_association",
            ["dataset_collection_id"],
            ["id"],
        )


def downgrade():
    with transaction():
        drop_table(association_table_name)
