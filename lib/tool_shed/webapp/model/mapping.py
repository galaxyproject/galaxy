"""
Details of how the data model objects are mapped onto the relational database
are encapsulated here.
"""
import logging

from sqlalchemy import Boolean, Column, DateTime, desc, false, ForeignKey, Integer, Table, TEXT, true
from sqlalchemy.orm import relation

import tool_shed.webapp.model
import tool_shed.webapp.util.shed_statistics as shed_statistics
from galaxy.model.base import SharedModelMapping
from galaxy.model.custom_types import MutableJSONType, TrimmedString
from galaxy.model.orm.engine_factory import build_engine
from galaxy.model.orm.now import now
from tool_shed.webapp.model import ComponentReview
from tool_shed.webapp.model import mapper_registry
from tool_shed.webapp.model import Repository, RepositoryCategoryAssociation
from tool_shed.webapp.model import RepositoryMetadata, RepositoryRatingAssociation
from tool_shed.webapp.model import RepositoryReview, RepositoryRoleAssociation
from tool_shed.webapp.model import User
from tool_shed.webapp.security import CommunityRBACAgent

log = logging.getLogger(__name__)

metadata = mapper_registry.metadata

Repository.table = Table("repository", metadata,
                         Column("id", Integer, primary_key=True),
                         Column("create_time", DateTime, default=now),
                         Column("update_time", DateTime, default=now, onupdate=now),
                         Column("name", TrimmedString(255), index=True),
                         Column("type", TrimmedString(255), index=True),
                         Column("remote_repository_url", TrimmedString(255)),
                         Column("homepage_url", TrimmedString(255)),
                         Column("description", TEXT),
                         Column("long_description", TEXT),
                         Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                         Column("private", Boolean, default=False),
                         Column("deleted", Boolean, index=True, default=False),
                         Column("email_alerts", MutableJSONType, nullable=True),
                         Column("times_downloaded", Integer),
                         Column("deprecated", Boolean, default=False))

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

RepositoryReview.table = Table("repository_review", metadata,
                               Column("id", Integer, primary_key=True),
                               Column("create_time", DateTime, default=now),
                               Column("update_time", DateTime, default=now, onupdate=now),
                               Column("repository_id", Integer, ForeignKey("repository.id"), index=True),
                               Column("changeset_revision", TrimmedString(255), index=True),
                               Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True, nullable=False),
                               Column("approved", TrimmedString(255)),
                               Column("rating", Integer, index=True),
                               Column("deleted", Boolean, index=True, default=False))

mapper_registry.map_imperatively(Repository, Repository.table,
       properties=dict(
           categories=relation(RepositoryCategoryAssociation, back_populates='repository'),
           ratings=relation(RepositoryRatingAssociation, order_by=desc(RepositoryRatingAssociation.update_time), back_populates='repository'),
           user=relation(User, back_populates='active_repositories'),
           downloadable_revisions=relation(RepositoryMetadata,
                                           primaryjoin=((Repository.table.c.id == RepositoryMetadata.table.c.repository_id) & (RepositoryMetadata.table.c.downloadable == true())),
                                           order_by=desc(RepositoryMetadata.table.c.update_time)),
           metadata_revisions=relation(RepositoryMetadata,
                                       order_by=desc(RepositoryMetadata.table.c.update_time)),
           roles=relation(RepositoryRoleAssociation, back_populates='repository'),
           reviews=relation(RepositoryReview, back_populates='repository'),
           reviewers=relation(User,
                              secondary=RepositoryReview.table,
                              primaryjoin=(Repository.table.c.id == RepositoryReview.table.c.repository_id),
                              secondaryjoin=(RepositoryReview.table.c.user_id == User.id))))

mapper_registry.map_imperatively(RepositoryMetadata, RepositoryMetadata.table,
       properties=dict(repository=relation(Repository),
                       reviews=relation(RepositoryReview,
                                        foreign_keys=[RepositoryMetadata.table.c.repository_id, RepositoryMetadata.table.c.changeset_revision],
                                        primaryjoin=((RepositoryMetadata.table.c.repository_id == RepositoryReview.table.c.repository_id) & (RepositoryMetadata.table.c.changeset_revision == RepositoryReview.table.c.changeset_revision)))))

mapper_registry.map_imperatively(RepositoryReview, RepositoryReview.table,
       properties=dict(repository=relation(Repository, back_populates='reviews'),
                       # Take care when using the mapper below!  It should be used only when a new review is being created for a repository change set revision.
                       # Keep in mind that repository_metadata records can be removed from the database for certain change set revisions when metadata is being
                       # reset on a repository!
                       repository_metadata=relation(RepositoryMetadata,
                                                    foreign_keys=[RepositoryReview.table.c.repository_id, RepositoryReview.table.c.changeset_revision],
                                                    primaryjoin=((RepositoryReview.table.c.repository_id == RepositoryMetadata.table.c.repository_id) & (RepositoryReview.table.c.changeset_revision == RepositoryMetadata.table.c.changeset_revision))),
                       user=relation(User, back_populates="repository_reviews"),
                       component_reviews=relation(ComponentReview,
                                                  primaryjoin=((RepositoryReview.table.c.id == ComponentReview.repository_review_id) & (ComponentReview.deleted == false())),
                                                  back_populates='repository_review'),
                       private_component_reviews=relation(ComponentReview,
                                                          primaryjoin=((RepositoryReview.table.c.id == ComponentReview.repository_review_id) & (ComponentReview.deleted == false()) & (ComponentReview.private == true())))))


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

    # Load local tool shed security policy
    result.security_agent = CommunityRBACAgent(result)
    result.shed_counter = shed_statistics.ShedCounter(result)
    return result
