"""
Adds requires_domain column to InteractiveTools Entry Point (interactivetool_entry_point).
"""
import datetime
import logging

from sqlalchemy import (
    Boolean,
    Column,
    MetaData,
)

from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column,
)

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    requires_domain = Column("requires_domain", Boolean, default=None)
    add_column(requires_domain, "interactivetool_entry_point", metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column("requires_domain", "interactivetool_entry_point", metadata)
