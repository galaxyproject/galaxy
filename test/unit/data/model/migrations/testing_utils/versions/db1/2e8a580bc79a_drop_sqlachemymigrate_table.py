"""drop sqlachemymigrate table

Revision ID: 2e8a580bc79a
Revises: 62695fac6cc0
Create Date: 2021-11-05 16:29:19.123118

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2e8a580bc79a"
down_revision = "62695fac6cc0"
branch_labels = None
depends_on = None


def upgrade():
    # This table exists in both schemas: gxy and tsi. With a combined database,
    # this migration will be applied twice to the same database, so we ignore
    # the error that happens on the second run when the table has been dropped.
    try:
        op.drop_table("migrate_version", must_exist=True)
    except sa.exc.InvalidRequestError:
        pass


def downgrade():
    op.create_table(
        "migrate_version",
        sa.Column("repository_id", sa.String(250), primary_key=True),
        sa.Column("repository_path", sa.Text),
        sa.Column("version", sa.Integer),
    )
