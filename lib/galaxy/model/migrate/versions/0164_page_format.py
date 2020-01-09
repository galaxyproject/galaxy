"""
Adds page content format.
"""
import datetime
import logging

from sqlalchemy import Column, MetaData

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import add_column, drop_column

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    content_format_column = Column('content_format', TrimmedString(32), default='html', server_default="html", nullable=False)
    add_column(content_format_column, 'page_revision', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('content_format', 'page_revision', metadata)
