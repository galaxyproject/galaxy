"""Create user_dynamic_tool_association table

Revision ID: f070559879f1
Revises: 75348cfb3715
Create Date: 2024-12-06 14:56:18.494243

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = "f070559879f1"
down_revision = "71eeb8d91f92"
branch_labels = None
depends_on = None


def upgrade():
    # Create user_dynamic_tool_association table
    op.create_table(
        "user_dynamic_tool_association",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("dynamic_tool_id", sa.Integer, sa.ForeignKey("dynamic_tool.id"), index=True, nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("galaxy_user.id"), index=True, nullable=False),
        sa.Column("create_time", sa.DateTime, nullable=True, server_default=func.now()),
        sa.Column("hidden", sa.Boolean, nullable=True, server_default=sa.text("false")),
        sa.Column("active", sa.Boolean, nullable=True, server_default=sa.text("true")),
    )

    # Add the public column with a default value of False
    op.add_column("dynamic_tool", sa.Column("public", sa.Boolean, nullable=False, server_default=sa.text("false")))
    # Update existing rows (these have been created by admins) to make them public
    op.execute("UPDATE dynamic_tool SET public = TRUE")


def downgrade():
    # Drop user_dynamic_tool_association table
    op.drop_table("user_dynamic_tool_association")
    op.drop_column("dynamic_tool", "public")
