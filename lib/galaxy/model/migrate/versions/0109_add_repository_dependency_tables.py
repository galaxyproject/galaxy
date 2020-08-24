"""
Migration script to add the repository_dependency and repository_repository_dependency_association tables.
"""

import datetime
import logging

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Table
)

from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
metadata = MetaData()

RepositoryDependency_table = Table("repository_dependency", metadata,
                                   Column("id", Integer, primary_key=True),
                                   Column("create_time", DateTime, default=now),
                                   Column("update_time", DateTime, default=now, onupdate=now),
                                   Column("tool_shed_repository_id", Integer, ForeignKey("tool_shed_repository.id"), index=True, nullable=False))

RepositoryRepositoryDependencyAssociation_table = Table("repository_repository_dependency_association", metadata,
                                                        Column("id", Integer, primary_key=True),
                                                        Column("create_time", DateTime, default=now),
                                                        Column("update_time", DateTime, default=now, onupdate=now),
                                                        Column("tool_shed_repository_id", Integer, ForeignKey("tool_shed_repository.id"), index=True),
                                                        Column("repository_dependency_id", Integer, ForeignKey("repository_dependency.id"), index=True))


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    create_table(RepositoryDependency_table)
    create_table(RepositoryRepositoryDependencyAssociation_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_table(RepositoryRepositoryDependencyAssociation_table)
    drop_table(RepositoryDependency_table)
