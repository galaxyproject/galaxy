"""Chat exchange storage.

Revision ID: cbc46035eba0
Revises: b855b714e8b8
Create Date: 2023-06-05 13:23:42.050738

"""

# from alembic import op
# import sqlalchemy as sa

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Text,
)

from galaxy.model.migrations.util import (
    create_table,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "cbc46035eba0"
down_revision = "a99a5b52ccb8"
branch_labels = None
depends_on = None


def upgrade():
    create_table(
        "chat_exchange",
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, ForeignKey("galaxy_user.id")),
        Column("job_id", Integer, ForeignKey("job.id"), nullable=True),
    )

    create_table(
        "chat_exchange_message",
        Column("id", Integer, primary_key=True),
        Column("chat_exchange_id", Integer, ForeignKey("chat_exchange.id")),
        Column("create_time", DateTime),
        Column("message", Text),
        Column("feedback", Integer, nullable=True),
    )


def downgrade():
    drop_table("chat_exchange_message")
    drop_table("chat_exchange")
