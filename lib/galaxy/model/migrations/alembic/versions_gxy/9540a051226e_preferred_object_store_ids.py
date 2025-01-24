"""preferred_object_store_ids

Revision ID: 9540a051226e
Revises: d0583094c8cd
Create Date: 2022-06-10 10:38:25.212102

"""

from sqlalchemy import (
    Column,
    String,
)

from galaxy.model.custom_types import JSONType
from galaxy.model.migrations.util import (
    add_column,
    drop_column,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "9540a051226e"
down_revision = "d0583094c8cd"
branch_labels = None
depends_on = None


def upgrade():
    with transaction():
        preferred_object_store_type = String(255)
        add_column("galaxy_user", Column("preferred_object_store_id", preferred_object_store_type, default=None))
        add_column("history", Column("preferred_object_store_id", preferred_object_store_type, default=None))
        add_column("job", Column("preferred_object_store_id", preferred_object_store_type, default=None))
        add_column("job", Column("object_store_id_overrides", JSONType))


def downgrade():
    with transaction():
        drop_column("galaxy_user", "preferred_object_store_id")
        drop_column("history", "preferred_object_store_id")
        drop_column("job", "preferred_object_store_id")
        drop_column("job", "object_store_id_overrides")
