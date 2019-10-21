"""
Adds reports_config to workflow.
"""
import datetime
import logging

from sqlalchemy import Column, MetaData

from galaxy.model.custom_types import JSONType
from galaxy.model.migrate.versions.util import add_column, drop_column

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()

    reports_config_column = Column('reports_config', JSONType, default=None)
    add_column(reports_config_column, 'workflow', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('reports_config', 'workflow', metadata)
