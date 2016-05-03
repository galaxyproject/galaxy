"""
Details of how the data model objects are mapped onto the relational database
are encapsulated here.
"""
import logging

from sqlalchemy import Boolean, Column, DateTime, desc, false, ForeignKey, Integer, MetaData, not_, String, Table, TEXT, true, UniqueConstraint
from sqlalchemy.orm import backref, mapper, relation

import galaxy.webapps.tool_shed.model
import galaxy.webapps.tool_shed.util.hgweb_config
import galaxy.webapps.tool_shed.util.shed_statistics as shed_statistics
from galaxy.model.base import ModelMapping
from galaxy.model.custom_types import JSONType, TrimmedString
from galaxy.model.orm.engine_factory import build_engine
from galaxy.model.orm.now import now
from galaxy.webapps.tool_shed.model import APIKeys, Category, Component, ComponentReview
from galaxy.webapps.tool_shed.model import GalaxySession, Group, GroupRoleAssociation
from galaxy.webapps.tool_shed.model import PasswordResetToken, Repository, RepositoryCategoryAssociation
from galaxy.webapps.tool_shed.model import RepositoryMetadata, RepositoryRatingAssociation
from galaxy.webapps.tool_shed.model import RepositoryReview, RepositoryRoleAssociation, Role
from galaxy.webapps.tool_shed.model import Tag, User, UserGroupAssociation, UserRoleAssociation
from galaxy.webapps.tool_shed.security import CommunityRBACAgent

log = logging.getLogger( __name__ )
metadata = MetaData()


APIKeys.table = Table( "api_keys", metadata,
                       Column( "id", Integer, primary_key=True ),
                       Column( "create_time", DateTime, default=now ),
                       Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
                       Column( "key", TrimmedString( 32 ), index=True, unique=True ) )

User.table = Table( "galaxy_user", metadata,
                    Column( "id", Integer, primary_key=True),
                    Column( "create_time", DateTime, default=now ),
                    Column( "update_time", DateTime, default=now, onupdate=now ),
                    Column( "email", TrimmedString( 255 ), nullable=False ),
                    Column( "username", String( 255 ), index=True ),
                    Column( "password", TrimmedString( 40 ), nullable=False ),
                    Column( "external", Boolean, default=False ),
                    Column( "new_repo_alert", Boolean, default=False ),
                    Column( "deleted", Boolean, index=True, default=False ),
                    Column( "purged", Boolean, index=True, default=False ) )

PasswordResetToken.table = Table("password_reset_token", metadata,
                                 Column( "token", String( 32 ), primary_key=True, unique=True, index=True ),
                                 Column( "expiration_time", DateTime ),
                                 Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ) )

Group.table = Table( "galaxy_group", metadata,
                     Column( "id", Integer, primary_key=True ),
                     Column( "create_time", DateTime, default=now ),
                     Column( "update_time", DateTime, default=now, onupdate=now ),
                     Column( "name", String( 255 ), index=True, unique=True ),
                     Column( "deleted", Boolean, index=True, default=False ) )

Role.table = Table( "role", metadata,
                    Column( "id", Integer, primary_key=True ),
                    Column( "create_time", DateTime, default=now ),
                    Column( "update_time", DateTime, default=now, onupdate=now ),
                    Column( "name", String( 255 ), index=True, unique=True ),
                    Column( "description", TEXT ),
                    Column( "type", String( 40 ), index=True ),
                    Column( "deleted", Boolean, index=True, default=False ) )

UserGroupAssociation.table = Table( "user_group_association", metadata,
                                    Column( "id", Integer, primary_key=True ),
                                    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
                                    Column( "group_id", Integer, ForeignKey( "galaxy_group.id" ), index=True ),
                                    Column( "create_time", DateTime, default=now ),
                                    Column( "update_time", DateTime, default=now, onupdate=now ) )

UserRoleAssociation.table = Table( "user_role_association", metadata,
                                   Column( "id", Integer, primary_key=True ),
                                   Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
                                   Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
                                   Column( "create_time", DateTime, default=now ),
                                   Column( "update_time", DateTime, default=now, onupdate=now ) )

GroupRoleAssociation.table = Table( "group_role_association", metadata,
                                    Column( "id", Integer, primary_key=True ),
                                    Column( "group_id", Integer, ForeignKey( "galaxy_group.id" ), index=True ),
                                    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
                                    Column( "create_time", DateTime, default=now ),
                                    Column( "update_time", DateTime, default=now, onupdate=now ) )

RepositoryRoleAssociation.table = Table( "repository_role_association", metadata,
                                         Column( "id", Integer, primary_key=True ),
                                         Column( "repository_id", Integer, ForeignKey( "repository.id" ), index=True ),
                                         Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
                                         Column( "create_time", DateTime, default=now ),
                                         Column( "update_time", DateTime, default=now, onupdate=now ) )

GalaxySession.table = Table( "galaxy_session", metadata,
                             Column( "id", Integer, primary_key=True ),
                             Column( "create_time", DateTime, default=now ),
                             Column( "update_time", DateTime, default=now, onupdate=now ),
                             Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=True ),
                             Column( "remote_host", String( 255 ) ),
                             Column( "remote_addr", String( 255 ) ),
                             Column( "referer", TEXT ),
                             Column( "session_key", TrimmedString( 255 ), index=True, unique=True ),  # unique 128 bit random number coerced to a string
                             Column( "is_valid", Boolean, default=False ),
                             Column( "prev_session_id", Integer ),  # saves a reference to the previous session so we have a way to chain them together
                             Column( "last_action", DateTime) )

Repository.table = Table( "repository", metadata,
                          Column( "id", Integer, primary_key=True ),
                          Column( "create_time", DateTime, default=now ),
                          Column( "update_time", DateTime, default=now, onupdate=now ),
                          Column( "name", TrimmedString( 255 ), index=True ),
                          Column( "type", TrimmedString( 255 ), index=True ),
                          Column( "remote_repository_url", TrimmedString( 255 ) ),
                          Column( "homepage_url", TrimmedString( 255 ) ),
                          Column( "description", TEXT ),
                          Column( "long_description", TEXT ),
                          Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
                          Column( "private", Boolean, default=False ),
                          Column( "deleted", Boolean, index=True, default=False ),
                          Column( "email_alerts", JSONType, nullable=True ),
                          Column( "times_downloaded", Integer ),
                          Column( "deprecated", Boolean, default=False ) )

RepositoryMetadata.table = Table( "repository_metadata", metadata,
                                  Column( "id", Integer, primary_key=True ),
                                  Column( "create_time", DateTime, default=now ),
                                  Column( "update_time", DateTime, default=now, onupdate=now ),
                                  Column( "repository_id", Integer, ForeignKey( "repository.id" ), index=True ),
                                  Column( "changeset_revision", TrimmedString( 255 ), index=True ),
                                  Column( "metadata", JSONType, nullable=True ),
                                  Column( "tool_versions", JSONType, nullable=True ),
                                  Column( "malicious", Boolean, default=False ),
                                  Column( "downloadable", Boolean, default=True ),
                                  Column( "missing_test_components", Boolean, default=False, index=True ),
                                  Column( "has_repository_dependencies", Boolean, default=False, index=True ),
                                  Column( "includes_datatypes", Boolean, default=False, index=True ),
                                  Column( "includes_tools", Boolean, default=False, index=True ),
                                  Column( "includes_tool_dependencies", Boolean, default=False, index=True ),
                                  Column( "includes_workflows", Boolean, default=False, index=True ) )

RepositoryReview.table = Table( "repository_review", metadata,
                                Column( "id", Integer, primary_key=True ),
                                Column( "create_time", DateTime, default=now ),
                                Column( "update_time", DateTime, default=now, onupdate=now ),
                                Column( "repository_id", Integer, ForeignKey( "repository.id" ), index=True ),
                                Column( "changeset_revision", TrimmedString( 255 ), index=True ),
                                Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
                                Column( "approved", TrimmedString( 255 ) ),
                                Column( "rating", Integer, index=True ),
                                Column( "deleted", Boolean, index=True, default=False ) )

ComponentReview.table = Table( "component_review", metadata,
                               Column( "id", Integer, primary_key=True ),
                               Column( "create_time", DateTime, default=now ),
                               Column( "update_time", DateTime, default=now, onupdate=now ),
                               Column( "repository_review_id", Integer, ForeignKey( "repository_review.id" ), index=True ),
                               Column( "component_id", Integer, ForeignKey( "component.id" ), index=True ),
                               Column( "comment", TEXT ),
                               Column( "private", Boolean, default=False ),
                               Column( "approved", TrimmedString( 255 ) ),
                               Column( "rating", Integer ),
                               Column( "deleted", Boolean, index=True, default=False ) )

Component.table = Table( "component", metadata,
                         Column( "id", Integer, primary_key=True ),
                         Column( "name", TrimmedString( 255 ) ),
                         Column( "description", TEXT ) )

RepositoryRatingAssociation.table = Table( "repository_rating_association", metadata,
                                           Column( "id", Integer, primary_key=True ),
                                           Column( "create_time", DateTime, default=now ),
                                           Column( "update_time", DateTime, default=now, onupdate=now ),
                                           Column( "repository_id", Integer, ForeignKey( "repository.id" ), index=True ),
                                           Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
                                           Column( "rating", Integer, index=True ),
                                           Column( "comment", TEXT ) )

RepositoryCategoryAssociation.table = Table( "repository_category_association", metadata,
                                             Column( "id", Integer, primary_key=True ),
                                             Column( "repository_id", Integer, ForeignKey( "repository.id" ), index=True ),
                                             Column( "category_id", Integer, ForeignKey( "category.id" ), index=True ) )

Category.table = Table( "category", metadata,
                        Column( "id", Integer, primary_key=True ),
                        Column( "create_time", DateTime, default=now ),
                        Column( "update_time", DateTime, default=now, onupdate=now ),
                        Column( "name", TrimmedString( 255 ), index=True, unique=True ),
                        Column( "description", TEXT ),
                        Column( "deleted", Boolean, index=True, default=False ) )

Tag.table = Table( "tag", metadata,
                   Column( "id", Integer, primary_key=True ),
                   Column( "type", Integer ),
                   Column( "parent_id", Integer, ForeignKey( "tag.id" ) ),
                   Column( "name", TrimmedString(255) ),
                   UniqueConstraint( "name" ) )

# With the tables defined we can define the mappers and setup the relationships between the model objects.
mapper( User, User.table,
        properties=dict( active_repositories=relation( Repository, primaryjoin=( ( Repository.table.c.user_id == User.table.c.id ) & ( not_( Repository.table.c.deleted ) ) ), order_by=( Repository.table.c.name ) ),
                         galaxy_sessions=relation( GalaxySession, order_by=desc( GalaxySession.table.c.update_time ) ),
                         api_keys=relation( APIKeys, backref="user", order_by=desc( APIKeys.table.c.create_time ) ) ) )

mapper( PasswordResetToken, PasswordResetToken.table,
        properties=dict( user=relation( User, backref="reset_tokens") ) )

mapper( APIKeys, APIKeys.table, properties={} )

mapper( Group, Group.table,
        properties=dict( users=relation( UserGroupAssociation ) ) )

mapper( Role, Role.table,
        properties=dict(
            repositories=relation( RepositoryRoleAssociation,
                                   primaryjoin=( ( Role.table.c.id == RepositoryRoleAssociation.table.c.role_id ) & ( RepositoryRoleAssociation.table.c.repository_id == Repository.table.c.id ) ) ),
            users=relation( UserRoleAssociation,
                            primaryjoin=( ( Role.table.c.id == UserRoleAssociation.table.c.role_id ) & ( UserRoleAssociation.table.c.user_id == User.table.c.id ) ) ),
            groups=relation( GroupRoleAssociation,
                             primaryjoin=( ( Role.table.c.id == GroupRoleAssociation.table.c.role_id ) & ( GroupRoleAssociation.table.c.group_id == Group.table.c.id ) ) ) ) )

mapper( RepositoryRoleAssociation, RepositoryRoleAssociation.table,
        properties=dict(
            repository=relation( Repository ),
            role=relation( Role ) ) )

mapper( UserGroupAssociation, UserGroupAssociation.table,
        properties=dict( user=relation( User, backref="groups" ),
                         group=relation( Group, backref="members" ) ) )

mapper( UserRoleAssociation, UserRoleAssociation.table,
        properties=dict(
            user=relation( User, backref="roles" ),
            non_private_roles=relation( User,
                                        backref="non_private_roles",
                                        primaryjoin=( ( User.table.c.id == UserRoleAssociation.table.c.user_id ) & ( UserRoleAssociation.table.c.role_id == Role.table.c.id ) & not_( Role.table.c.name == User.table.c.email ) ) ),
            role=relation( Role ) ) )

mapper( GroupRoleAssociation, GroupRoleAssociation.table,
        properties=dict(
            group=relation( Group, backref="roles" ),
            role=relation( Role ) ) )

mapper( GalaxySession, GalaxySession.table,
        properties=dict( user=relation( User ) ) )

mapper( Tag, Tag.table,
        properties=dict( children=relation(Tag, backref=backref( 'parent', remote_side=[ Tag.table.c.id ] ) ) ) )

mapper( Category, Category.table,
        properties=dict( repositories=relation( RepositoryCategoryAssociation,
                                                secondary=Repository.table,
                                                primaryjoin=( Category.table.c.id == RepositoryCategoryAssociation.table.c.category_id ),
                                                secondaryjoin=( RepositoryCategoryAssociation.table.c.repository_id == Repository.table.c.id ) ) ) )

mapper( Repository, Repository.table,
        properties=dict(
            categories=relation( RepositoryCategoryAssociation ),
            ratings=relation( RepositoryRatingAssociation, order_by=desc( RepositoryRatingAssociation.table.c.update_time ), backref="repositories" ),
            user=relation( User ),
            downloadable_revisions=relation( RepositoryMetadata,
                                             primaryjoin=( ( Repository.table.c.id == RepositoryMetadata.table.c.repository_id ) & ( RepositoryMetadata.table.c.downloadable == true() ) ),
                                             order_by=desc( RepositoryMetadata.table.c.update_time ) ),
            metadata_revisions=relation( RepositoryMetadata,
                                         order_by=desc( RepositoryMetadata.table.c.update_time ) ),
            roles=relation( RepositoryRoleAssociation ),
            reviews=relation( RepositoryReview,
                              primaryjoin=( ( Repository.table.c.id == RepositoryReview.table.c.repository_id ) ) ),
            reviewers=relation( User,
                                secondary=RepositoryReview.table,
                                primaryjoin=( Repository.table.c.id == RepositoryReview.table.c.repository_id ),
                                secondaryjoin=( RepositoryReview.table.c.user_id == User.table.c.id ) ) ) )

mapper( RepositoryMetadata, RepositoryMetadata.table,
        properties=dict( repository=relation( Repository ),
                         reviews=relation( RepositoryReview,
                                           foreign_keys=[ RepositoryMetadata.table.c.repository_id, RepositoryMetadata.table.c.changeset_revision ],
                                           primaryjoin=( ( RepositoryMetadata.table.c.repository_id == RepositoryReview.table.c.repository_id ) & ( RepositoryMetadata.table.c.changeset_revision == RepositoryReview.table.c.changeset_revision ) ) ) ) )

mapper( RepositoryReview, RepositoryReview.table,
        properties=dict( repository=relation( Repository,
                                              primaryjoin=( RepositoryReview.table.c.repository_id == Repository.table.c.id ) ),
                         # Take care when using the mapper below!  It should be used only when a new review is being created for a repository change set revision.
                         # Keep in mind that repository_metadata records can be removed from the database for certain change set revisions when metadata is being
                         # reset on a repository!
                         repository_metadata=relation( RepositoryMetadata,
                                                       foreign_keys=[ RepositoryReview.table.c.repository_id, RepositoryReview.table.c.changeset_revision ],
                                                       primaryjoin=( ( RepositoryReview.table.c.repository_id == RepositoryMetadata.table.c.repository_id ) & ( RepositoryReview.table.c.changeset_revision == RepositoryMetadata.table.c.changeset_revision ) ),
                                                       backref='review' ),
                         user=relation( User, backref="repository_reviews" ),
                         component_reviews=relation( ComponentReview,
                                                     primaryjoin=( ( RepositoryReview.table.c.id == ComponentReview.table.c.repository_review_id ) & ( ComponentReview.table.c.deleted == false() ) ) ),
                         private_component_reviews=relation( ComponentReview,
                                                             primaryjoin=( ( RepositoryReview.table.c.id == ComponentReview.table.c.repository_review_id ) & ( ComponentReview.table.c.deleted == false() ) & ( ComponentReview.table.c.private == true() ) ) ) ) )

mapper( ComponentReview, ComponentReview.table,
        properties=dict( repository_review=relation( RepositoryReview ),
                         component=relation( Component,
                                             primaryjoin=( ComponentReview.table.c.component_id == Component.table.c.id ) ) ) )

mapper( Component, Component.table )

mapper( RepositoryRatingAssociation, RepositoryRatingAssociation.table,
        properties=dict( repository=relation( Repository ), user=relation( User ) ) )

mapper( RepositoryCategoryAssociation, RepositoryCategoryAssociation.table,
        properties=dict(
            category=relation( Category ),
            repository=relation( Repository ) ) )


def init( file_path, url, engine_options={}, create_tables=False ):
    """Connect mappings to the database"""
    # Create the database engine
    engine = build_engine( url, engine_options )
    # Connect the metadata to the database.
    metadata.bind = engine

    result = ModelMapping([galaxy.webapps.tool_shed.model], engine=engine)

    if create_tables:
        metadata.create_all()

    result.create_tables = create_tables

    # Load local tool shed security policy
    result.security_agent = CommunityRBACAgent( result )
    result.shed_counter = shed_statistics.ShedCounter( result )
    result.hgweb_config_manager = galaxy.webapps.tool_shed.util.hgweb_config.HgWebConfigManager()
    return result
