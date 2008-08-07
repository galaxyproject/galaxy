"""
Details of how the data model objects are mapped onto the relational database
are encapsulated here. 
"""
import logging
log = logging.getLogger( __name__ )

import pkg_resources
pkg_resources.require( "sqlalchemy>=0.3" )

import sys
import datetime

from sqlalchemy.ext.sessioncontext import SessionContext
from sqlalchemy.ext.assignmapper import assign_mapper
from sqlalchemy.ext.orderinglist import ordering_list

from sqlalchemy import *
from galaxy.model import *
from galaxy.model.custom_types import *
from galaxy.util.bunch import Bunch
from galaxy.security import GalaxyRBACAgent

metadata = DynamicMetaData( threadlocal=False )
context = SessionContext( create_session ) 

dialect_to_egg = { 
    "sqlite"   : "pysqlite>=2",
    "postgres" : "psycopg2",
    "mysql"    : "MySQL_python"
}

# NOTE REGARDING TIMESTAMPS:
#   It is currently difficult to have the timestamps calculated by the 
#   database in a portable way, so we're doing it in the client. This
#   also saves us from needing to postfetch on postgres. HOWEVER: it
#   relies on the client's clock being set correctly, so if clustering
#   web servers, use a time server to ensure synchronization

# Return the current time in UTC without any timezone information
now = datetime.datetime.utcnow

User.table = Table( "galaxy_user", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "email", TrimmedString( 255 ), nullable=False ),
    Column( "password", TrimmedString( 40 ), nullable=False ),
    Column( "external", Boolean, default=False ) )
            
History.table = Table( "history", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "name", TrimmedString( 255 ) ),
    Column( "hid_counter", Integer, default=1 ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ),
    Column( "genome_build", TrimmedString( 40 ) ) )

# model.Query.table = Table( "query", engine,
#             Column( "id", Integer, primary_key=True),
#             Column( "history_id", Integer, ForeignKey( "history.id" ) ),
#             Column( "name", String( 255 ) ),
#             Column( "state", String( 64 ) ),
#             Column( "tool_parameters", Pickle() ) )


HistoryDatasetAssociation.table = Table( "history_dataset_association", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "copied_from_history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), nullable=True ),
    Column( "hid", Integer ),
    Column( "name", TrimmedString( 255 ) ),
    Column( "info", TrimmedString( 255 ) ),
    Column( "blurb", TrimmedString( 255 ) ),
    Column( "peek" , TEXT ),
    Column( "extension", TrimmedString( 64 ) ),
    Column( "metadata", MetadataType(), key="_metadata" ),
    Column( "parent_id", Integer, ForeignKey( "history_dataset_association.id" ), nullable=True ),
    Column( "designation", TrimmedString( 255 ) ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "visible", Boolean ) )

Dataset.table = Table( "dataset", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "state", TrimmedString( 64 ) ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ),
    Column( "purgable", Boolean, default=True ),
    Column( "external_filename" , TEXT ),
    Column( "_extra_files_path", TEXT ),
    Column( 'file_size', Numeric( 15, 0 ) ) )

ImplicitlyConvertedDatasetAssociation.table = Table( "implicitly_converted_dataset_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "hda_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True, nullable=True ),
    Column( "hda_parent_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "metadata_safe", Boolean, index=True, default=True ),
    Column( "type", TrimmedString( 255 ) ) )

ValidationError.table = Table( "validation_error", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "dataset_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "message", TrimmedString( 255 ) ),
    Column( "err_type", TrimmedString( 64 ) ),
    Column( "attributes", TEXT ) )

Group.table = Table( "galaxy_group", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TEXT ),
    Column( "priority", Integer ) )

UserGroupAssociation.table = Table( "user_group_association", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "group_id", Integer, ForeignKey( "galaxy_group.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

Permission.table = Table( "permission", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TEXT ),
    Column( "actions", JSONType(), default=[] ) )

Role.table = Table( "role", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TEXT ),
    Column( "priority", Integer ) )

RolePermissionAssociation.table = Table( "role_permission_association", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
    Column( "permission_id", Integer, ForeignKey( "permission.id" ), index=True ),
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

GroupDatasetAssociation.table = Table( "group_dataset_association", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "group_id", Integer, ForeignKey( "galaxy_group.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

RoleDatasetAssociation.table = Table( "role_dataset_association", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

RoleControlRoleAssociation.table = Table( "role_control_role_association", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
    Column( "target_role_id", Integer, ForeignKey( "role.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

GroupControlRoleAssociation.table = Table( "group_control_role_association", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
    Column( "group_id", Integer, ForeignKey( "galaxy_group.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )


DefaultUserRoleAssociation.table = Table( "default_user_role_association", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

DefaultUserGroupAssociation.table = Table( "default_user_group_association", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "group_id", Integer, ForeignKey( "galaxy_group.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

DefaultHistoryRoleAssociation.table = Table( "default_history_role_association", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

DefaultHistoryGroupAssociation.table = Table( "default_history_group_association", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "group_id", Integer, ForeignKey( "galaxy_group.id" ), index=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

Job.table = Table( "job", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "tool_id", String( 255 ) ),
    Column( "tool_version", String, default="1.0.0" ),
    Column( "state", String( 64 ) ),
    Column( "info", TrimmedString( 255 ) ),
    Column( "command_line", String() ), 
    Column( "param_filename", String( 1024 ) ),
    Column( "runner_name", String( 255 ) ),
    Column( "stdout", String() ),
    Column( "stderr", String() ),
    Column( "traceback", String() ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), index=True, nullable=True ),
    Column( "job_runner_name", String( 255 ) ),
    Column( "job_runner_external_id", String( 255 ) ) )
    
JobParameter.table = Table( "job_parameter", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "name", String(255) ),
    Column( "value", TEXT ) )
    
JobToInputDatasetAssociation.table = Table( "job_to_input_dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "name", String(255) ) )
    
JobToOutputDatasetAssociation.table = Table( "job_to_output_dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "name", String(255) ) )
    
Event.table = Table( "event", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True, nullable=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=True ),
    Column( "message", TrimmedString( 1024 ) ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), index=True, nullable=True ),
    Column( "tool_id", String( 255 ) ) )

GalaxySession.table = Table( "galaxy_session", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=True ),
    Column( "remote_host", String( 255 ) ),
    Column( "remote_addr", String( 255 ) ),
    Column( "referer", TEXT ),
    Column( "current_history_id", Integer, ForeignKey( "history.id" ), nullable=True ),
    Column( "session_key", TrimmedString( 255 ), index=True, unique=True ), # unique 128 bit random number coerced to a string
    Column( "is_valid", Boolean, default=False ),
    Column( "prev_session_id", Integer ) # saves a reference to the previous session so we have a way to chain them together
    )

GalaxySessionToHistoryAssociation.table = Table( "galaxy_session_to_history", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), index=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ) )

StoredWorkflow.table = Table( "stored_workflow", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
    Column( "latest_workflow_id", Integer,
            ForeignKey( "workflow.id", use_alter=True, name='stored_workflow_latest_workflow_id_fk' ), index=True ),
    Column( "name", String ),
    Column( "deleted", Boolean, default=False ),
    )

Workflow.table = Table( "workflow", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True, nullable=False ),
    Column( "name", String ),
    Column( "has_cycles", Boolean ),
    Column( "has_errors", Boolean )
    )

WorkflowStep.table = Table( "workflow_step", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "workflow_id", Integer, ForeignKey( "workflow.id" ), index=True, nullable=False ),
    Column( "type", String(64) ),
    Column( "tool_id", String ),
    Column( "tool_version", String ), # Reserved for future
    Column( "tool_inputs", JSONType ),
    Column( "tool_errors", JSONType ),
    Column( "position", JSONType ),
    Column( "config", JSONType ),
    Column( "order_index", Integer ),
    ## Column( "input_connections", JSONType )
    )

WorkflowStepConnection.table = Table( "workflow_step_connection", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "output_step_id", Integer, ForeignKey( "workflow_step.id" ), index=True ),
    Column( "input_step_id", Integer, ForeignKey( "workflow_step.id" ), index=True ),
    Column( "output_name", String ),
    Column( "input_name", String)
    )

StoredWorkflowUserShareAssociation.table = Table( "stored_workflow_user_share_connection", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True )
    )

StoredWorkflowMenuEntry.table = Table( "stored_workflow_menu_entry", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),                              
    Column( "order_index", Integer ) )

# With the tables defined we can define the mappers and setup the 
# relationships between the model objects.

assign_mapper( context, ValidationError, ValidationError.table )

assign_mapper( context, HistoryDatasetAssociation, HistoryDatasetAssociation.table,
    properties=dict( 
        dataset=relation( 
            Dataset, 
            primaryjoin=( Dataset.table.c.id == HistoryDatasetAssociation.table.c.dataset_id ), lazy=False ),
        history=relation( 
            History, 
            primaryjoin=( History.table.c.id == HistoryDatasetAssociation.table.c.history_id ) ),
        copied_to_history_dataset_associations=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( HistoryDatasetAssociation.table.c.copied_from_history_dataset_association_id == HistoryDatasetAssociation.table.c.id ),
            backref=backref( "copied_from_history_dataset_association", primaryjoin=( HistoryDatasetAssociation.table.c.copied_from_history_dataset_association_id == HistoryDatasetAssociation.table.c.id ), remote_side=[HistoryDatasetAssociation.table.c.id] ) ),
        implicitly_converted_datasets=relation( 
            ImplicitlyConvertedDatasetAssociation, 
            primaryjoin=( ImplicitlyConvertedDatasetAssociation.table.c.hda_parent_id == HistoryDatasetAssociation.table.c.id ) ),
        children=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( HistoryDatasetAssociation.table.c.parent_id == HistoryDatasetAssociation.table.c.id ),
            backref=backref( "parent", primaryjoin=( HistoryDatasetAssociation.table.c.parent_id == HistoryDatasetAssociation.table.c.id ), remote_side=[HistoryDatasetAssociation.table.c.id] ) )
            ) )

assign_mapper( context, Dataset, Dataset.table,
    properties=dict( 
        history_associations=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( Dataset.table.c.id == HistoryDatasetAssociation.table.c.dataset_id ) )
            ) )


# assign_mapper( model.Query, model.Query.table,
#     properties=dict( datasets=relation( model.Dataset.mapper, backref="query") ) )


assign_mapper( context, ImplicitlyConvertedDatasetAssociation, ImplicitlyConvertedDatasetAssociation.table, 
    properties=dict( parent=relation( 
                     HistoryDatasetAssociation, 
                     primaryjoin=( ImplicitlyConvertedDatasetAssociation.table.c.hda_parent_id == HistoryDatasetAssociation.table.c.id ) ),
                     
                     dataset=relation( 
                     HistoryDatasetAssociation, 
                     primaryjoin=( ImplicitlyConvertedDatasetAssociation.table.c.hda_id == HistoryDatasetAssociation.table.c.id ) ) ) )

assign_mapper( context, History, History.table,
    properties=dict( galaxy_sessions=relation( GalaxySessionToHistoryAssociation ),
                     datasets=relation( HistoryDatasetAssociation, backref="history", order_by=asc(HistoryDatasetAssociation.table.c.hid) ),
                     active_datasets=relation( HistoryDatasetAssociation, primaryjoin=( ( HistoryDatasetAssociation.table.c.history_id == History.table.c.id ) & ( not_( HistoryDatasetAssociation.table.c.deleted ) ) ), order_by=asc( HistoryDatasetAssociation.table.c.hid ), lazy=False, viewonly=True ) ) )

assign_mapper( context, User, User.table, 
    properties=dict( histories=relation( History, backref="user", 
                                         order_by=desc(History.table.c.update_time) ),
                     stored_workflow_menu_entries=relation( StoredWorkflowMenuEntry, backref="user",
                                                            cascade="all, delete-orphan",
                                                            collection_class=ordering_list( 'order_index' ) )
                     ) )

assign_mapper( context, Group, Group.table,
    properties=dict( users=relation( UserGroupAssociation ),
                     datasets=relation( GroupDatasetAssociation ) ) )

assign_mapper( context, UserGroupAssociation, UserGroupAssociation.table,
    properties=dict( user=relation( User, backref = "groups" ),
                     group=relation( Group, backref = "users" ) ) )

assign_mapper( context, UserRoleAssociation, UserRoleAssociation.table,
    properties=dict( role=relation( Role, backref = "users" ),
                     user=relation( User, backref = "roles" ) ) )

assign_mapper( context, GroupRoleAssociation, GroupRoleAssociation.table,
    properties=dict( role=relation( Role, backref = "groups" ),
                     group=relation( Group, backref = "roles" ) ) )

assign_mapper( context, Permission, Permission.table )

assign_mapper( context, Role, Role.table )

assign_mapper( context, RolePermissionAssociation, RolePermissionAssociation.table,
    properties=dict( role=relation( Role, backref = "permissions" ),
                     permission=relation( Permission, backref = "roles" ) ) )


assign_mapper( context, GroupDatasetAssociation, GroupDatasetAssociation.table,
    properties=dict( dataset=relation( Dataset, backref = "groups" ),
                     group=relation( Group, backref = "datasets" ) ) )

assign_mapper( context, RoleDatasetAssociation, RoleDatasetAssociation.table,
    properties=dict( dataset=relation( Dataset, backref = "roles" ),
                     role=relation( Role ) ) )

assign_mapper( context, RoleControlRoleAssociation, RoleControlRoleAssociation.table,
    properties=dict( role=relation( Role, primaryjoin=( ( RoleControlRoleAssociation.table.c.role_id == Role.table.c.id ) ) ),
                     target_role=relation( Role, primaryjoin=( RoleControlRoleAssociation.table.c.target_role_id == Role.table.c.id ), backref="roles" ) ) )

assign_mapper( context, GroupControlRoleAssociation, GroupControlRoleAssociation.table,
    properties=dict( role=relation( Role, backref="access_groups" ),
                     group=relation( Group, backref="access_roles" ) ) )

assign_mapper( context, DefaultUserRoleAssociation, DefaultUserRoleAssociation.table,
    properties=dict( user=relation( User, backref = "default_roles" ),
                     role=relation( Role ) ) )

assign_mapper( context, DefaultUserGroupAssociation, DefaultUserGroupAssociation.table,
    properties=dict( user=relation( User, backref = "default_groups" ),
                     group=relation( Group ) ) )

assign_mapper( context, DefaultHistoryRoleAssociation, DefaultHistoryRoleAssociation.table,
    properties=dict( history=relation( History, backref = "default_roles" ),
                     role=relation( Role ) ) )

assign_mapper( context, DefaultHistoryGroupAssociation, DefaultHistoryGroupAssociation.table,
    properties=dict( history=relation( History, backref = "default_groups" ),
                     group=relation( Group ) ) )

assign_mapper( context, JobToInputDatasetAssociation, JobToInputDatasetAssociation.table,
    properties=dict( job=relation( Job ), dataset=relation( HistoryDatasetAssociation ) ) )

assign_mapper( context, JobToOutputDatasetAssociation, JobToOutputDatasetAssociation.table,
    properties=dict( job=relation( Job ), dataset=relation( HistoryDatasetAssociation ) ) )

assign_mapper( context, JobParameter, JobParameter.table )

assign_mapper( context, Job, Job.table, 
    properties=dict( galaxy_session=relation( GalaxySession ),
                     history=relation( History ),
                     parameters=relation( JobParameter ),
                     input_datasets=relation( JobToInputDatasetAssociation ),
                     output_datasets=relation( JobToOutputDatasetAssociation ) ) )

assign_mapper( context, Event, Event.table,
    properties=dict( history=relation( History ),
                     galaxy_session=relation( GalaxySession ),
                     user=relation( User.mapper ) ) )

assign_mapper( context, GalaxySession, GalaxySession.table,
    properties=dict( histories=relation( GalaxySessionToHistoryAssociation ),
                     user=relation( User.mapper ) ) )

assign_mapper( context, GalaxySessionToHistoryAssociation, GalaxySessionToHistoryAssociation.table,
    properties=dict( galaxy_session=relation( GalaxySession ), 
                     history=relation( History ) ) )

HistoryDatasetAssociation.mapper.add_property( "creating_job_associations", relation( JobToOutputDatasetAssociation ) )

assign_mapper( context, Workflow, Workflow.table,
    properties=dict( steps=relation( WorkflowStep, backref='workflow',
                                     order_by=asc(WorkflowStep.table.c.order_index),
                                     cascade="all, delete-orphan",
                                     lazy=False ) ) )

    
assign_mapper( context, WorkflowStep, WorkflowStep.table )

assign_mapper( context, WorkflowStepConnection, WorkflowStepConnection.table,
    properties=dict( input_step=relation( WorkflowStep, backref="input_connections", cascade="all",
                                          primaryjoin=( WorkflowStepConnection.table.c.input_step_id == WorkflowStep.table.c.id ) ),
                     output_step=relation( WorkflowStep, backref="output_connections", cascade="all",
                                           primaryjoin=( WorkflowStepConnection.table.c.output_step_id == WorkflowStep.table.c.id ) ) ) )

assign_mapper( context, StoredWorkflow, StoredWorkflow.table,
    properties=dict( user=relation( User ),
                     workflows=relation( Workflow, backref='stored_workflow',
                                         cascade="all, delete-orphan",
                                         primaryjoin=( StoredWorkflow.table.c.id == Workflow.table.c.stored_workflow_id ) ),
                     latest_workflow=relation( Workflow, post_update=True,
                                               primaryjoin=( StoredWorkflow.table.c.latest_workflow_id == Workflow.table.c.id ),
                                               lazy=False )
                   ) )

assign_mapper( context, StoredWorkflowUserShareAssociation, StoredWorkflowUserShareAssociation.table,
    properties=dict( user=relation( User, backref='workflows_shared_by_others' ),
                     stored_workflow=relation( StoredWorkflow )
                   ) )

assign_mapper( context, StoredWorkflowMenuEntry, StoredWorkflowMenuEntry.table,
    properties=dict( stored_workflow=relation( StoredWorkflow ) ) )

def db_next_hid( self ):
    """
    Override __next_hid to generate from the database in a concurrency
    safe way.
    """
    conn = self.table.engine.contextual_connect()
    trans = conn.begin()
    try:
        next_hid = select( [self.c.hid_counter], self.c.id == self.id, for_update=True ).scalar()
        self.table.update( self.c.id == self.id ).execute( hid_counter = ( next_hid + 1 ) )
        trans.commit()
        return next_hid
    except:
        trans.rollback()
        raise

History._next_hid = db_next_hid
    
def init( file_path, url, engine_options={}, create_tables=False ):
    """Connect mappings to the database"""
    # Connect dataset to the file path
    Dataset.file_path = file_path
    # Load the appropriate db module
    dialect = (url.split(':', 1))[0]
    try:
        egg = dialect_to_egg[dialect]
        try:
            pkg_resources.require( egg )
            log.debug( "%s egg successfully loaded for %s dialect" % ( egg, dialect ) )
        except:
            # If the module's in the path elsewhere (i.e. non-egg), it'll still load.
            log.warning( "%s egg not found, but an attempt will be made to use %s anyway" % ( egg, dialect ) )
    except KeyError:
        # Let this go, it could possibly work with db's we don't support
        log.error( "database_connection contains an unknown SQLAlchemy database dialect: %s" % dialect )
    # Create the database engine
    engine = create_engine( url, **engine_options )
    # Connect the metadata to the database.
    metadata.connect( engine )
    ## metadata.engine.echo = True
    # Create tables if needed
    if create_tables:
        metadata.create_all()
        # metadata.engine.commit()
    # Pack everything into a bunch
    result = Bunch( **globals() )
    result.engine = metadata.engine
    result.flush = lambda *args, **kwargs: context.current.flush( *args, **kwargs )
    result.context = context
    result.create_tables = create_tables
    #load local galaxy security policy
    result.security_agent = GalaxyRBACAgent( result )
    #set up default table entries here, currently only exist for access controls
    if result.Role.count() == 0:
        log.warning( "There were no access roles located, setting up default (public) access roles." )
        #create public group
        public_group = result.Group( 'public' )
        public_group.flush()
        #create public_all role
        public_role = result.Role( 'public' )
        public_role.flush()
        result.security_agent.associate_components( group = public_group, role = public_role )
        permission = result.Permission( 'public', [ result.Dataset.access_actions.USE, result.Dataset.access_actions.VIEW, result.Group.access_actions.ADD_DATASET, result.Group.access_actions.REMOVE_DATASET ] )
        permission.flush()
        result.security_agent.associate_components( permission = permission, role = public_role )
        
        #store public group id
        Group.public_id = public_group.id #we use the id instead of the object, because of alchemy sessions
        
        #loop through all histories and set up rbac on users, histories and datasets
        for history in result.History.select():
            if history.user:
                if not history.user.default_groups:
                    results.security_agent.setup_new_user( history.user )
                    history.user.flush()
            else:
                result.security_agent.history_set_default_access( history, dataset = True )
                history.flush()
        #add all datasets which aren't in a history to the public group
        orphans = result.Dataset.get_by( history_id = None )
        if orphans:
            for dataset in orphans:
                result.security_agent.set_dataset_groups( dataset, [ public_group ] )
                result.security_agent.set_dataset_roles( dataset, [] )
    else:
        #retrieve from database and store public group id, assume first created group is public
        Group.public_id = result.Group.select( order_by = asc( result.Group.table.c.create_time ) )[0].id #we use the id instead of the object, because of alchemy sessions
    log.debug( "Public Group identified as id = %s." % ( Group.public_id ) )
    return result
    
def get_suite():
    """Get unittest suite for this module"""
    import unittest, mapping_tests
    return unittest.makeSuite( mapping_tests.MappingTests )
