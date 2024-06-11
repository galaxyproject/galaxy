"""Update username column schema and data

Revision ID: c63848676caf
Revises: c14a3c93d66b
Create Date: 2024-06-11 13:41:36.411803

"""

from alembic import op
from sqlalchemy import (
    or_,
    select,
    update,
)

from galaxy.managers.users import username_from_email_with_connection
from galaxy.model import User
from galaxy.model.migrations.util import (
    alter_column,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "c63848676caf"
down_revision = "c14a3c93d66b"
branch_labels = None
depends_on = None

table_name = "galaxy_user"
column_name = "username"


def upgrade():
    with transaction():
        _generate_missing_usernames()
        alter_column(table_name, column_name, nullable=False)


def downgrade():
    with transaction():
        # The data migration is one-way: we can change back the database schema,
        # but we can't remove the generated username values.
        alter_column(table_name, column_name, nullable=True)


def _generate_missing_usernames():
    stmt = select(User.id, User.email).where(or_(User.username.is_(None), User.username == ""))
    connection = op.get_bind()
    users = connection.execute(stmt).all()
    for id, email in users:
        new_username = username_from_email_with_connection(connection, email)
        stmt = update(User).where(User.id == id).values(username=new_username)
        connection.execute(stmt)
