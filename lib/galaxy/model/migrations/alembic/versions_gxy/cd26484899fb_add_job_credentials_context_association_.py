"""add job credentials context association table

Revision ID: cd26484899fb
Revises: c8c9bd29810d
Create Date: 2025-09-12 16:39:02.143639

"""

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
)

from galaxy.model.migrations.util import (
    create_table,
    drop_table,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "cd26484899fb"
down_revision = "c8c9bd29810d"
branch_labels = None
depends_on = None

job_credentials_context_association_table = "job_credentials_context"


def upgrade():
    with transaction():
        create_table(
            job_credentials_context_association_table,
            Column("id", Integer, primary_key=True),
            Column("job_id", Integer, ForeignKey("job.id"), index=True),
            Column(
                "user_credentials_id",
                Integer,
                ForeignKey("user_credentials.id", ondelete="SET NULL"),
                index=True,
                nullable=True,
            ),
            Column("service_name", String(255)),
            Column("service_version", String(255)),
            Column(
                "selected_group_id",
                Integer,
                ForeignKey("credentials_group.id", ondelete="SET NULL"),
                index=True,
                nullable=True,
            ),
            Column("selected_group_name", String(255)),
        )


def downgrade():
    with transaction():
        drop_table(job_credentials_context_association_table)
