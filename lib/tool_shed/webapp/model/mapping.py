"""
Details of how the data model objects are mapped onto the relational database
are encapsulated here.
"""
import logging

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Table
from sqlalchemy.orm import relation

import tool_shed.webapp.model
import tool_shed.webapp.util.shed_statistics as shed_statistics
from galaxy.model.base import SharedModelMapping
from galaxy.model.custom_types import MutableJSONType, TrimmedString
from galaxy.model.orm.engine_factory import build_engine
from galaxy.model.orm.now import now
from tool_shed.webapp.model import mapper_registry
from tool_shed.webapp.model import Repository
from tool_shed.webapp.model import RepositoryMetadata
from tool_shed.webapp.model import RepositoryReview
from tool_shed.webapp.security import CommunityRBACAgent

log = logging.getLogger(__name__)

metadata = mapper_registry.metadata

RepositoryMetadata.table = Table("repository_metadata", metadata,
                                 Column("id", Integer, primary_key=True),
                                 Column("create_time", DateTime, default=now),
                                 Column("update_time", DateTime, default=now, onupdate=now),
                                 Column("repository_id", Integer, ForeignKey("repository.id"), index=True),
                                 Column("changeset_revision", TrimmedString(255), index=True),
                                 Column("numeric_revision", Integer, index=True),
                                 Column("metadata", MutableJSONType, nullable=True),
                                 Column("tool_versions", MutableJSONType, nullable=True),
                                 Column("malicious", Boolean, default=False),
                                 Column("downloadable", Boolean, default=True),
                                 Column("missing_test_components", Boolean, default=False, index=True),
                                 Column("has_repository_dependencies", Boolean, default=False, index=True),
                                 Column("includes_datatypes", Boolean, default=False, index=True),
                                 Column("includes_tools", Boolean, default=False, index=True),
                                 Column("includes_tool_dependencies", Boolean, default=False, index=True),
                                 Column("includes_workflows", Boolean, default=False, index=True))

mapper_registry.map_imperatively(RepositoryMetadata, RepositoryMetadata.table, properties=dict(
    repository=relation(Repository, back_populates='metadata_revisions'),
    reviews=relation(RepositoryReview,
        viewonly=True,
        foreign_keys=[RepositoryReview.repository_id, RepositoryReview.changeset_revision],
        primaryjoin=((RepositoryReview.repository_id == RepositoryMetadata.table.c.repository_id) & (RepositoryReview.changeset_revision == RepositoryMetadata.table.c.changeset_revision)),
        back_populates='repository_metadata')))


class ToolShedModelMapping(SharedModelMapping):
    security_agent: CommunityRBACAgent
    shed_counter: shed_statistics.ShedCounter
    create_tables: bool


def init(file_path, url, engine_options=None, create_tables=False) -> ToolShedModelMapping:
    """Connect mappings to the database"""
    engine_options = engine_options or {}
    # Create the database engine
    engine = build_engine(url, engine_options)
    # Connect the metadata to the database.
    metadata.bind = engine

    result = ToolShedModelMapping([tool_shed.webapp.model], engine=engine)

    if create_tables:
        metadata.create_all()

    result.create_tables = create_tables

    result.security_agent = CommunityRBACAgent(result)
    result.shed_counter = shed_statistics.ShedCounter(result)
    return result
