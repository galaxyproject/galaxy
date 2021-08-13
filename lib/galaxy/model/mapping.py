"""
Details of how the data model objects are mapped onto the relational database
are encapsulated here.
"""

import logging
from threading import local
from typing import Optional, Type

from sqlalchemy import (
    and_,
    Boolean,
    Column,
    DateTime,
    desc,
    ForeignKey,
    Integer,
    not_,
    Numeric,
    select,
    Table,
    TEXT,
    true,
)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import class_mapper, column_property, deferred, object_session, relation
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.sql import exists

from galaxy import model
from galaxy.model import mapper_registry
from galaxy.model.base import SharedModelMapping
from galaxy.model.custom_types import (
    JSONType,
    TrimmedString,
)
from galaxy.model.migrate.triggers.update_audit_table import install as install_timestamp_triggers
from galaxy.model.orm.engine_factory import build_engine
from galaxy.model.orm.now import now
from galaxy.model.security import GalaxyRBACAgent
from galaxy.model.view.utils import install_views

log = logging.getLogger(__name__)

metadata = mapper_registry.metadata


model.User.table = Table(
    "galaxy_user", metadata,
    Column("id", Integer, primary_key=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now),
    Column("email", TrimmedString(255), index=True, nullable=False),
    Column("username", TrimmedString(255), index=True, unique=True),
    Column("password", TrimmedString(255), nullable=False),
    Column("last_password_change", DateTime, default=now),
    Column("external", Boolean, default=False),
    Column("form_values_id", Integer, ForeignKey("form_values.id"), index=True),
    Column("deleted", Boolean, index=True, default=False),
    Column("purged", Boolean, index=True, default=False),
    Column("disk_usage", Numeric(15, 0), index=True),
    # Column("person_metadata", JSONType),  # TODO: add persistent, configurable metadata rep for workflow creator
    Column("active", Boolean, index=True, default=True, nullable=False),
    Column("activation_token", TrimmedString(64), nullable=True, index=True))

model.HistoryDatasetAssociation.table = Table(
    "history_dataset_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("history_id", Integer, ForeignKey("history.id"), index=True),
    Column("dataset_id", Integer, ForeignKey("dataset.id"), index=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now, index=True),
    Column("state", TrimmedString(64), index=True, key="_state"),
    Column("copied_from_history_dataset_association_id", Integer,
           ForeignKey("history_dataset_association.id"), nullable=True),
    Column("copied_from_library_dataset_dataset_association_id", Integer,
           ForeignKey("library_dataset_dataset_association.id"), nullable=True),
    Column("name", TrimmedString(255)),
    Column("info", TrimmedString(255)),
    Column("blurb", TrimmedString(255)),
    Column("peek", TEXT, key="_peek"),
    Column("tool_version", TEXT),
    Column("extension", TrimmedString(64)),
    Column("metadata", JSONType, key="_metadata"),
    Column("parent_id", Integer, ForeignKey("history_dataset_association.id"), nullable=True),
    Column("designation", TrimmedString(255)),
    Column("deleted", Boolean, index=True, default=False),
    Column("visible", Boolean),
    Column("extended_metadata_id", Integer, ForeignKey("extended_metadata.id"), index=True),
    Column("version", Integer, default=1, nullable=True, index=True),
    Column("hid", Integer),
    Column("purged", Boolean, index=True, default=False),
    Column("validated_state", TrimmedString(64), default='unvalidated', nullable=False),
    Column("validated_state_message", TEXT),
    Column("hidden_beneath_collection_instance_id",
           ForeignKey("history_dataset_collection_association.id"), nullable=True))


model.LibraryDatasetDatasetAssociation.table = Table(
    "library_dataset_dataset_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("library_dataset_id", Integer, ForeignKey("library_dataset.id"), index=True),
    Column("dataset_id", Integer, ForeignKey("dataset.id"), index=True),
    Column("create_time", DateTime, default=now),
    Column("update_time", DateTime, default=now, onupdate=now, index=True),
    Column("state", TrimmedString(64), index=True, key="_state"),
    Column("copied_from_history_dataset_association_id", Integer,
        ForeignKey("history_dataset_association.id", use_alter=True, name='history_dataset_association_dataset_id_fkey'),
        nullable=True),

    Column("copied_from_library_dataset_dataset_association_id", Integer,
        ForeignKey("library_dataset_dataset_association.id", use_alter=True, name='library_dataset_dataset_association_id_fkey'),
        nullable=True),

    Column("name", TrimmedString(255), index=True),
    Column("info", TrimmedString(255)),
    Column("blurb", TrimmedString(255)),
    Column("peek", TEXT, key="_peek"),
    Column("tool_version", TEXT),
    Column("extension", TrimmedString(64)),
    Column("metadata", JSONType, key="_metadata"),
    Column("parent_id", Integer, ForeignKey("library_dataset_dataset_association.id"), nullable=True),
    Column("designation", TrimmedString(255)),
    Column("deleted", Boolean, index=True, default=False),
    Column("validated_state", TrimmedString(64), default='unvalidated', nullable=False),
    Column("validated_state_message", TEXT),
    Column("visible", Boolean),
    Column("extended_metadata_id", Integer, ForeignKey("extended_metadata.id"), index=True),
    Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
    Column("message", TrimmedString(255)))


# With the tables defined we can define the mappers and setup the
# relationships between the model objects.
def simple_mapping(model, **kwds):
    mapper_registry.map_imperatively(model, model.table, properties=kwds)


simple_mapping(model.HistoryDatasetAssociation,
    dataset=relation(model.Dataset,
        primaryjoin=(model.Dataset.id == model.HistoryDatasetAssociation.table.c.dataset_id),
        lazy=False,
        backref='history_associations'),
    # .history defined in History mapper
    copied_from_history_dataset_association=relation(model.HistoryDatasetAssociation,
        primaryjoin=(model.HistoryDatasetAssociation.table.c.copied_from_history_dataset_association_id
                     == model.HistoryDatasetAssociation.table.c.id),
        remote_side=[model.HistoryDatasetAssociation.table.c.id],
        uselist=False,
        backref='copied_to_history_dataset_associations'),
    copied_to_library_dataset_dataset_associations=relation(model.LibraryDatasetDatasetAssociation,
        primaryjoin=(model.HistoryDatasetAssociation.table.c.id
                     == model.LibraryDatasetDatasetAssociation.table.c.copied_from_history_dataset_association_id),
        backref='copied_from_history_dataset_association'),
    tags=relation(model.HistoryDatasetAssociationTagAssociation,
        order_by=model.HistoryDatasetAssociationTagAssociation.id,
        back_populates='history_dataset_association'),
    annotations=relation(model.HistoryDatasetAssociationAnnotationAssociation,
        order_by=model.HistoryDatasetAssociationAnnotationAssociation.id,
        back_populates="hda"),
    ratings=relation(model.HistoryDatasetAssociationRatingAssociation,
        order_by=model.HistoryDatasetAssociationRatingAssociation.id,
        back_populates="history_dataset_association"),
    extended_metadata=relation(model.ExtendedMetadata,
        primaryjoin=(model.HistoryDatasetAssociation.table.c.extended_metadata_id
                     == model.ExtendedMetadata.id)),
    hidden_beneath_collection_instance=relation(model.HistoryDatasetCollectionAssociation,
        primaryjoin=(model.HistoryDatasetAssociation.table.c.hidden_beneath_collection_instance_id
                     == model.HistoryDatasetCollectionAssociation.id),
        uselist=False,
        backref="hidden_dataset_instances"),
    _metadata=deferred(model.HistoryDatasetAssociation.table.c._metadata),
    dependent_jobs=relation(model.JobToInputDatasetAssociation, back_populates='dataset'),
    creating_job_associations=relation(
        model.JobToOutputDatasetAssociation, back_populates='dataset'),
    history=relation(model.History, back_populates='datasets'),
    implicitly_converted_datasets=relation(model.ImplicitlyConvertedDatasetAssociation,
        primaryjoin=(lambda: model.ImplicitlyConvertedDatasetAssociation.hda_parent_id  # type: ignore
            == model.HistoryDatasetAssociation.id),  # type: ignore
        back_populates='parent_hda'),
    implicitly_converted_parent_datasets=relation(model.ImplicitlyConvertedDatasetAssociation,
        primaryjoin=(lambda: model.ImplicitlyConvertedDatasetAssociation.hda_id  # type: ignore
            == model.HistoryDatasetAssociation.id),  # type: ignore
        back_populates='dataset')
)

# Set up proxy so that
#   History.users_shared_with
# returns a list of users that history is shared with.
model.History.users_shared_with_dot_users = association_proxy('users_shared_with', 'user')  # type: ignore

mapper_registry.map_imperatively(model.User, model.User.table, properties=dict(
    addresses=relation(model.UserAddress,
        back_populates='user',
        order_by=desc(model.UserAddress.update_time)),
    cloudauthz=relation(model.CloudAuthz, back_populates='user'),
    custos_auth=relation(model.CustosAuthnzToken, back_populates='user'),
    default_permissions=relation(model.DefaultUserPermissions, back_populates='user'),
    groups=relation(model.UserGroupAssociation, back_populates='user'),
    histories=relation(model.History,
        backref="user",
        order_by=desc(model.History.update_time)),
    active_histories=relation(model.History,
        primaryjoin=(
            (model.History.user_id == model.User.table.c.id)
            & (not_(model.History.deleted))
        ),
        viewonly=True,
        order_by=desc(model.History.update_time)),
    galaxy_sessions=relation(model.GalaxySession,
        backref="user",
        order_by=desc(model.GalaxySession.update_time)),
    pages_shared_by_others=relation(model.PageUserShareAssociation, back_populates='user'),
    quotas=relation(model.UserQuotaAssociation, back_populates='user'),
    social_auth=relation(model.UserAuthnzToken, back_populates='user'),
    stored_workflow_menu_entries=relation(model.StoredWorkflowMenuEntry,
        primaryjoin=(
            (model.StoredWorkflowMenuEntry.user_id == model.User.table.c.id)
            & (model.StoredWorkflowMenuEntry.stored_workflow_id == model.StoredWorkflow.id)
            & not_(model.StoredWorkflow.deleted)
        ),
        backref="user",
        cascade="all, delete-orphan",
        collection_class=ordering_list('order_index')),
    _preferences=relation(model.UserPreference,
        backref="user",
        collection_class=attribute_mapped_collection('name')),
    values=relation(model.FormValues,
        primaryjoin=(model.User.table.c.form_values_id == model.FormValues.id)),
    api_keys=relation(model.APIKeys,
        back_populates="user",
        order_by=desc(model.APIKeys.create_time)),
    pages=relation(model.Page, back_populates='user'),
    reset_tokens=relation(model.PasswordResetToken, back_populates='user'),
    histories_shared_by_others=relation(
        model.HistoryUserShareAssociation, back_populates='user'),
    data_manager_histories=relation(model.DataManagerHistoryAssociation, back_populates='user'),
    workflows_shared_by_others=relation(model.StoredWorkflowUserShareAssociation, back_populates='user'),
    roles=relation(model.UserRoleAssociation, back_populates='user'),
    stored_workflows=relation(model.StoredWorkflow, back_populates='user',
        primaryjoin=(lambda: model.User.table.c.id == model.StoredWorkflow.user_id)),  # type: ignore
))

# Set up proxy so that this syntax is possible:
# <user_obj>.preferences[pref_name] = pref_value
model.User.preferences = association_proxy('_preferences', 'value', creator=model.UserPreference)  # type: ignore

mapper_registry.map_imperatively(model.LibraryDatasetDatasetAssociation, model.LibraryDatasetDatasetAssociation.table, properties=dict(
    dataset=relation(model.Dataset,
        primaryjoin=(model.LibraryDatasetDatasetAssociation.table.c.dataset_id == model.Dataset.id),
        backref='library_associations'),
    library_dataset=relation(model.LibraryDataset,
        foreign_keys=model.LibraryDatasetDatasetAssociation.table.c.library_dataset_id),
    # user=relation( model.User.mapper ),
    user=relation(model.User),
    copied_from_library_dataset_dataset_association=relation(model.LibraryDatasetDatasetAssociation,
        primaryjoin=(model.LibraryDatasetDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id
                     == model.LibraryDatasetDatasetAssociation.table.c.id),
        remote_side=[model.LibraryDatasetDatasetAssociation.table.c.id],
        uselist=False,
        backref='copied_to_library_dataset_dataset_associations'),
    copied_to_history_dataset_associations=relation(model.HistoryDatasetAssociation,
        primaryjoin=(model.LibraryDatasetDatasetAssociation.table.c.id
                     == model.HistoryDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id),
        backref='copied_from_library_dataset_dataset_association'),
    implicitly_converted_datasets=relation(model.ImplicitlyConvertedDatasetAssociation,
        primaryjoin=(model.ImplicitlyConvertedDatasetAssociation.ldda_parent_id
                     == model.LibraryDatasetDatasetAssociation.table.c.id),
        backref='parent_ldda'),
    tags=relation(model.LibraryDatasetDatasetAssociationTagAssociation,
                  order_by=model.LibraryDatasetDatasetAssociationTagAssociation.id,
                  back_populates='library_dataset_dataset_association'),
    extended_metadata=relation(model.ExtendedMetadata,
        primaryjoin=(model.LibraryDatasetDatasetAssociation.table.c.extended_metadata_id == model.ExtendedMetadata.id)
    ),
    _metadata=deferred(model.LibraryDatasetDatasetAssociation.table.c._metadata),
    actions=relation(
        model.LibraryDatasetDatasetAssociationPermissions,
        back_populates='library_dataset_dataset_association'),
    dependent_jobs=relation(
        model.JobToInputLibraryDatasetAssociation, back_populates='dataset'),
    creating_job_associations=relation(
        model.JobToOutputLibraryDatasetAssociation, back_populates='dataset'),
    implicitly_converted_parent_datasets=relation(model.ImplicitlyConvertedDatasetAssociation,
        primaryjoin=(lambda: model.ImplicitlyConvertedDatasetAssociation.ldda_id  # type: ignore
            == model.LibraryDatasetDatasetAssociation.id),  # type: ignore
        back_populates='dataset_ldda'),
))

# simple_mapping(
#     model.ImplicitCollectionJobsHistoryDatasetCollectionAssociation,
#     history_dataset_collection_associations=relation(
#         model.HistoryDatasetCollectionAssociation,
#         backref=backref("implicit_collection_jobs_association", uselist=False),
#         uselist=True,
#     ),
# )

# Set up proxy so that
#   StoredWorkflow.users_shared_with
# returns a list of users that workflow is shared with.
model.StoredWorkflow.users_shared_with_dot_users = association_proxy('users_shared_with', 'user')  # type: ignore

# Set up proxy so that
#   Page.users_shared_with
# returns a list of users that page is shared with.
model.Page.users_shared_with_dot_users = association_proxy('users_shared_with', 'user')  # type: ignore

# Set up proxy so that
#   Visualization.users_shared_with
# returns a list of users that visualization is shared with.
model.Visualization.users_shared_with_dot_users = association_proxy('users_shared_with', 'user')  # type: ignore

model.Job.any_output_dataset_deleted = column_property(  # type: ignore
    exists([model.HistoryDatasetAssociation],
           and_(model.Job.id == model.JobToOutputDatasetAssociation.job_id,
                model.HistoryDatasetAssociation.table.c.id == model.JobToOutputDatasetAssociation.dataset_id,
                model.HistoryDatasetAssociation.table.c.deleted == true())
           )
)
model.Job.any_output_dataset_collection_instances_deleted = column_property(  # type: ignore
    exists([model.HistoryDatasetCollectionAssociation.id],
           and_(model.Job.id == model.JobToOutputDatasetCollectionAssociation.job_id,
                model.HistoryDatasetCollectionAssociation.id == model.JobToOutputDatasetCollectionAssociation.dataset_collection_id,
                model.HistoryDatasetCollectionAssociation.deleted == true())
           )
)

class_mapper(model.HistoryDatasetCollectionAssociation).add_property(
    "creating_job_associations", relation(model.JobToOutputDatasetCollectionAssociation, viewonly=True))


# Helper methods.
def db_next_hid(self, n=1):
    """
    db_next_hid( self )

    Override __next_hid to generate from the database in a concurrency safe way.
    Loads the next history ID from the DB and returns it.
    It also saves the future next_id into the DB.

    :rtype:     int
    :returns:   the next history id
    """
    session = object_session(self)
    table = self.table
    trans = session.begin()
    try:
        if "postgres" not in session.bind.dialect.name:
            next_hid = select([table.c.hid_counter], table.c.id == model.cached_id(self)).with_for_update().scalar()
            table.update(table.c.id == self.id).execute(hid_counter=(next_hid + n))
        else:
            stmt = table.update().where(table.c.id == model.cached_id(self)).values(hid_counter=(table.c.hid_counter + n)).returning(table.c.hid_counter)
            next_hid = session.execute(stmt).scalar() - n
        trans.commit()
        return next_hid
    except Exception:
        trans.rollback()
        raise


model.History._next_hid = db_next_hid  # type: ignore


def _workflow_invocation_update(self):
    session = object_session(self)
    table = self.table
    now_val = now()
    stmt = table.update().values(update_time=now_val).where(and_(table.c.id == self.id, table.c.update_time < now_val))
    session.execute(stmt)


model.WorkflowInvocation.update = _workflow_invocation_update  # type: ignore


class GalaxyModelMapping(SharedModelMapping):
    security_agent: GalaxyRBACAgent
    thread_local_log: Optional[local]
    create_tables: bool
    User: Type
    GalaxySession: Type


def init(file_path, url, engine_options=None, create_tables=False, map_install_models=False,
        database_query_profiling_proxy=False, object_store=None, trace_logger=None, use_pbkdf2=True,
        slow_query_log_threshold=0, thread_local_log: Optional[local] = None, log_query_counts=False) -> GalaxyModelMapping:
    """Connect mappings to the database"""
    if engine_options is None:
        engine_options = {}
    # Connect dataset to the file path
    model.Dataset.file_path = file_path
    # Connect dataset to object store
    model.Dataset.object_store = object_store
    # Use PBKDF2 password hashing?
    model.User.use_pbkdf2 = use_pbkdf2
    # Load the appropriate db module
    engine = build_engine(url, engine_options, database_query_profiling_proxy, trace_logger, slow_query_log_threshold, thread_local_log=thread_local_log, log_query_counts=log_query_counts)

    # Connect the metadata to the database.
    metadata.bind = engine

    model_modules = [model]
    if map_install_models:
        import galaxy.model.tool_shed_install.mapping  # noqa: F401
        from galaxy.model import tool_shed_install
        galaxy.model.tool_shed_install.mapping.init(url=url, engine_options=engine_options, create_tables=create_tables)
        model_modules.append(tool_shed_install)

    result = GalaxyModelMapping(model_modules, engine=engine)

    # Create tables if needed
    if create_tables:
        metadata.create_all()
        install_timestamp_triggers(engine)
        install_views(engine)

    result.create_tables = create_tables
    # load local galaxy security policy
    result.security_agent = GalaxyRBACAgent(result)
    result.thread_local_log = thread_local_log
    return result
