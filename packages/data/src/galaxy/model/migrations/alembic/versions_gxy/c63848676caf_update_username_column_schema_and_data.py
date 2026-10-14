"""Update username column schema and data

Revision ID: c63848676caf
Revises: c14a3c93d66b
Create Date: 2024-06-11 13:41:36.411803

"""

import string

from alembic import op
from sqlalchemy import (
    or_,
    select,
    update,
)

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
        new_username = username_from_email(connection, email)
        update_stmt = update(User).where(User.id == id).values(username=new_username)
        connection.execute(update_stmt)


# The code below is a near-duplicate of similar code in managers.users. The duplication is
# intentional: we want to preserve this logic in the migration script. The only differences are:
# (1) this code uses a Connection instead of a Session;
# (2) the username_exists function inlines the Select statement from managers.users::get_user_by_username.


def username_from_email(connection, email, model_class=User):
    # This function is also called from database revision scripts, which do not provide a session.
    username = email.split("@", 1)[0].lower()
    username = filter_out_invalid_username_characters(username)
    if username_exists(connection, username, model_class):
        username = generate_next_available_username(connection, username, model_class)
    return username


def filter_out_invalid_username_characters(username):
    """Replace invalid characters in username"""
    for char in [x for x in username if x not in f"{string.ascii_lowercase + string.digits}-."]:
        username = username.replace(char, "-")
    return username


def username_exists(connection, username: str, model_class=User):
    stmt = select(model_class).filter(model_class.username == username).limit(1)
    return bool(connection.execute(stmt).first())


def generate_next_available_username(connection, username, model_class=User):
    """Generate unique username; user can change it later"""
    i = 1
    while connection.execute(select(model_class).where(model_class.username == f"{username}-{i}")).first():
        i += 1
    return f"{username}-{i}"
