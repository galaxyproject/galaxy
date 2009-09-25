"""
Details of how the data model objects are mapped onto the relational database
are encapsulated here. 
"""
import logging
log = logging.getLogger( __name__ )

import sys
import datetime

from galaxy.model import *
from galaxy.model.orm import *
from galaxy.model.orm.ext.assignmapper import *
from galaxy.model.custom_types import *
from galaxy.util.bunch import Bunch
from galaxy.security import GalaxyRBACAgent

metadata = MetaData()
context = Session = scoped_session( sessionmaker( autoflush=False, transactional=False ) )

# For backward compatibility with "context.current"
context.current = Session

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
    Column( "username", TrimmedString( 255 ), index=True, unique=True ),
    Column( "password", TrimmedString( 40 ), nullable=False ),
    Column( "external", Boolean, default=False ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ) )

UserAddress.table = Table( "user_address", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "desc", TrimmedString( 255 )),    
    Column( "name", TrimmedString( 255 ), nullable=False),
    Column( "institution", TrimmedString( 255 )),
    Column( "address", TrimmedString( 255 ), nullable=False),
    Column( "city", TrimmedString( 255 ), nullable=False),
    Column( "state", TrimmedString( 255 ), nullable=False),
    Column( "postal_code", TrimmedString( 255 ), nullable=False),
    Column( "country", TrimmedString( 255 ), nullable=False),
    Column( "phone", TrimmedString( 255 )),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ) )

History.table = Table( "history", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "name", TrimmedString( 255 ) ),
    Column( "hid_counter", Integer, default=1 ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ),
    Column( "genome_build", TrimmedString( 40 ) ),
    Column( "importable", Boolean, default=False ) )

HistoryUserShareAssociation.table = Table( "history_user_share_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True )
    )

HistoryDatasetAssociation.table = Table( "history_dataset_association", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "copied_from_history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), nullable=True ),
    Column( "copied_from_library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), nullable=True ),
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
    Column( "state", TrimmedString( 64 ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ),
    Column( "purgable", Boolean, default=True ),
    Column( "external_filename" , TEXT ),
    Column( "_extra_files_path", TEXT ),
    Column( 'file_size', Numeric( 15, 0 ) ) )

HistoryDatasetAssociationDisplayAtAuthorization.table = Table( "history_dataset_association_display_at_authorization", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "site", TrimmedString( 255 ) ) )

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
    Column( "name", String( 255 ), index=True, unique=True ),
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

Role.table = Table( "role", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", String( 255 ), index=True, unique=True ),
    Column( "description", TEXT ),
    Column( "type", String( 40 ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

DatasetPermissions.table = Table( "dataset_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

LibraryPermissions.table = Table( "library_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "library_id", Integer, ForeignKey( "library.id" ), nullable=True, index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

LibraryFolderPermissions.table = Table( "library_folder_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "library_folder_id", Integer, ForeignKey( "library_folder.id" ), nullable=True, index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

LibraryDatasetPermissions.table = Table( "library_dataset_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "library_dataset_id", Integer, ForeignKey( "library_dataset.id" ), nullable=True, index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

LibraryDatasetDatasetAssociationPermissions.table = Table( "library_dataset_dataset_association_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), nullable=True, index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

DefaultUserPermissions.table = Table( "default_user_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "action", TEXT ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

DefaultHistoryPermissions.table = Table( "default_history_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "action", TEXT ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

LibraryDataset.table = Table( "library_dataset", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id", use_alter=True, name="library_dataset_dataset_association_id_fk" ), nullable=True, index=True ),#current version of dataset, if null, there is not a current version selected
    Column( "folder_id", Integer, ForeignKey( "library_folder.id" ), index=True ),
    Column( "order_id", Integer ), #not currently being used, but for possible future use
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), key="_name", index=True ), #when not None/null this will supercede display in library (but not when imported into user's history?)
    Column( "info", TrimmedString( 255 ),  key="_info" ), #when not None/null this will supercede display in library (but not when imported into user's history?)
    Column( "deleted", Boolean, index=True, default=False ) )

LibraryDatasetDatasetAssociation.table = Table( "library_dataset_dataset_association", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "library_dataset_id", Integer, ForeignKey( "library_dataset.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "copied_from_history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id", use_alter=True, name='history_dataset_association_dataset_id_fkey' ), nullable=True ),
    Column( "copied_from_library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id", use_alter=True, name='library_dataset_dataset_association_id_fkey' ), nullable=True ),
    Column( "name", TrimmedString( 255 ), index=True ),
    Column( "info", TrimmedString( 255 ) ),
    Column( "blurb", TrimmedString( 255 ) ),
    Column( "peek" , TEXT ),
    Column( "extension", TrimmedString( 64 ) ),
    Column( "metadata", MetadataType(), key="_metadata" ),
    Column( "parent_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), nullable=True ),
    Column( "designation", TrimmedString( 255 ) ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "visible", Boolean ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "message", TrimmedString( 255 ) ) )

Library.table = Table( "library", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "root_folder_id", Integer, ForeignKey( "library_folder.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", String( 255 ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ),
    Column( "description", TEXT ) )

LibraryFolder.table = Table( "library_folder", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "parent_id", Integer, ForeignKey( "library_folder.id" ), nullable = True, index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TEXT, index=True ),
    Column( "description", TEXT ),
    Column( "order_id", Integer ), #not currently being used, but for possible future use
    Column( "item_count", Integer ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ),
    Column( "genome_build", TrimmedString( 40 ) ) )

LibraryInfoAssociation.table = Table( 'library_info_association', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "library_id", Integer, ForeignKey( "library.id" ), index=True ),
    Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ) )

LibraryFolderInfoAssociation.table = Table( 'library_folder_info_association', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "library_folder_id", Integer, ForeignKey( "library_folder.id" ), nullable=True, index=True ),
    Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ) )

LibraryDatasetDatasetInfoAssociation.table = Table( 'library_dataset_dataset_info_association', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), nullable=True, index=True ),
    Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ) )

Job.table = Table( "job", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "library_folder_id", Integer, ForeignKey( "library_folder.id" ), index=True ),
    Column( "tool_id", String( 255 ) ),
    Column( "tool_version", TEXT, default="1.0.0" ),
    Column( "state", String( 64 ), index=True ),
    Column( "info", TrimmedString( 255 ) ),
    Column( "command_line", TEXT ), 
    Column( "param_filename", String( 1024 ) ),
    Column( "runner_name", String( 255 ) ),
    Column( "stdout", TEXT ),
    Column( "stderr", TEXT ),
    Column( "traceback", TEXT ),
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
    
JobToOutputLibraryDatasetAssociation.table = Table( "job_to_output_library_dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "ldda_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), index=True ),
    Column( "name", String(255) ) )
    
JobExternalOutputMetadata.table = Table( "job_external_output_metadata", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True, nullable=True ),
    Column( "library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), index=True, nullable=True ),
    Column( "filename_in", String( 255 ) ),
    Column( "filename_out", String( 255 ) ),
    Column( "filename_results_code", String( 255 ) ),
    Column( "filename_kwds", String( 255 ) ),
    Column( "job_runner_external_pid", String( 255 ) ) )
    
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
    Column( "name", TEXT ),
    Column( "deleted", Boolean, default=False ),
    Column( "importable", Boolean, default=False ),
    )

Workflow.table = Table( "workflow", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True, nullable=False ),
    Column( "name", TEXT ),
    Column( "has_cycles", Boolean ),
    Column( "has_errors", Boolean )
    )

WorkflowStep.table = Table( "workflow_step", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "workflow_id", Integer, ForeignKey( "workflow.id" ), index=True, nullable=False ),
    Column( "type", String(64) ),
    Column( "tool_id", TEXT ),
    Column( "tool_version", TEXT ), # Reserved for future
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
    Column( "output_name", TEXT ),
    Column( "input_name", TEXT)
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

MetadataFile.table = Table( "metadata_file", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "name", TEXT ),
    Column( "hda_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True, nullable=True ),
    Column( "lda_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), index=True, nullable=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ) )

FormDefinitionCurrent.table = Table('form_definition_current', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "latest_form_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ))

FormDefinition.table = Table('form_definition', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), nullable=False ),
    Column( "desc", TEXT ),
    Column( "form_definition_current_id",
            Integer, 
            ForeignKey( "form_definition_current.id", name='for_def_form_def_current_id_fk', use_alter=True ), 
            index=True ),
    Column( "fields", JSONType() ),
    Column( "type", TrimmedString( 255 ), index=True ),
    Column( "layout", JSONType() ), )

RequestType.table = Table('request_type', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), nullable=False ),
    Column( "desc", TEXT ),
    Column( "request_form_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "sample_form_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

FormValues.table = Table('form_values', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "content", JSONType()) )

Request.table = Table('request', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), nullable=False ),
    Column( "desc", TEXT ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
    Column( "request_type_id", Integer, ForeignKey( "request_type.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "library_id", Integer, ForeignKey( "library.id" ), index=True ),
    Column( "folder_id", Integer, ForeignKey( "library_folder.id" ), index=True ),
    Column( "state", TrimmedString( 255 ),  index=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

Sample.table = Table('sample', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), nullable=False ),
    Column( "desc", TEXT ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
    Column( "request_id", Integer, ForeignKey( "request.id" ), index=True ),
    Column( "bar_code", TrimmedString( 255 ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

SampleState.table = Table('sample_state', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), nullable=False ),
    Column( "desc", TEXT ),
    Column( "request_type_id", Integer, ForeignKey( "request_type.id" ), index=True ) )

SampleEvent.table = Table('sample_event', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "sample_id", Integer, ForeignKey( "sample.id" ), index=True ), 
    Column( "sample_state_id", Integer, ForeignKey( "sample_state.id" ), index=True ), 
    Column( "comment", TEXT ) )

Page.table = Table( "page", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
    Column( "latest_revision_id", Integer,
            ForeignKey( "page_revision.id", use_alter=True, name='page_latest_revision_id_fk' ), index=True ),
    Column( "title", TEXT ),
    Column( "slug", TEXT, unique=True, index=True ),
    )

PageRevision.table = Table( "page_revision", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True, nullable=False ),
    Column( "title", TEXT ),
    Column( "content", TEXT )
    )

Tag.table = Table( "tag", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "type", Integer ),
    Column( "parent_id", Integer, ForeignKey( "tag.id" ) ),
    Column( "name", TrimmedString(255) ), 
    UniqueConstraint( "name" ) )

HistoryTagAssociation.table = Table( "history_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )
    
DatasetTagAssociation.table = Table( "dataset_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

HistoryDatasetAssociationTagAssociation.table = Table( "history_dataset_association_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

PageTagAssociation.table = Table( "page_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )
    
UserPreference.table = Table( "user_preference", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "name", Unicode( 255 ), index=True),
    Column( "value", Unicode( 1024 ) ) )
    
# With the tables defined we can define the mappers and setup the 
# relationships between the model objects.

assign_mapper( context, Sample, Sample.table,
               properties=dict( 
                    events=relation( SampleEvent, backref="sample",
                        order_by=desc(SampleEvent.table.c.update_time) ),
                    values=relation( FormValues,
                        primaryjoin=( Sample.table.c.form_values_id == FormValues.table.c.id ) ),
                    request=relation( Request,
                        primaryjoin=( Sample.table.c.request_id == Request.table.c.id ) ),
            ) )

assign_mapper( context, FormValues, FormValues.table,
               properties=dict( form_definition=relation( FormDefinition,
                                                          primaryjoin=( FormValues.table.c.form_definition_id == FormDefinition.table.c.id ) )
             )
)

assign_mapper( context, Request, Request.table,
               properties=dict( values=relation( FormValues,
                                                 primaryjoin=( Request.table.c.form_values_id == FormValues.table.c.id ) ),
                                type=relation( RequestType,
                                               primaryjoin=( Request.table.c.request_type_id == RequestType.table.c.id ) ),
                                user=relation( User,
                                               primaryjoin=( Request.table.c.user_id == User.table.c.id ),
                                               backref="requests" ),
                                samples=relation( Sample,
                                                  primaryjoin=( Request.table.c.id == Sample.table.c.request_id ) ),
                                folder=relation( LibraryFolder,
                                                 primaryjoin=( Request.table.c.folder_id == LibraryFolder.table.c.id ) ),                 
                                library=relation( Library,
                                                  primaryjoin=( Request.table.c.library_id == Library.table.c.id ) )
                              ) )

assign_mapper( context, RequestType, RequestType.table,               
               properties=dict( states=relation( SampleState, 
                                                 backref="request_type",
                                                 primaryjoin=( RequestType.table.c.id == SampleState.table.c.request_type_id ),
                                                 order_by=asc(SampleState.table.c.update_time) ),
                                request_form=relation( FormDefinition,
                                                       primaryjoin=( RequestType.table.c.request_form_id == FormDefinition.table.c.id ) ),
                                sample_form=relation( FormDefinition,
                                                      primaryjoin=( RequestType.table.c.sample_form_id == FormDefinition.table.c.id ) ),
                              ) )

assign_mapper( context, FormDefinition, FormDefinition.table,
               properties=dict( current=relation( FormDefinitionCurrent,
                                                  primaryjoin=( FormDefinition.table.c.form_definition_current_id == FormDefinitionCurrent.table.c.id ) )
                              ) )
assign_mapper( context, FormDefinitionCurrent, FormDefinitionCurrent.table,
                properties=dict( forms=relation( FormDefinition, backref='form_definition_current',
                                                 cascade="all, delete-orphan",
                                                 primaryjoin=( FormDefinitionCurrent.table.c.id == FormDefinition.table.c.form_definition_current_id ) ),
                                 latest_form=relation( FormDefinition, post_update=True,
                                                       primaryjoin=( FormDefinitionCurrent.table.c.latest_form_id == FormDefinition.table.c.id ) )
                               ) )

assign_mapper( context, SampleEvent, SampleEvent.table, 
               properties=dict( state=relation( SampleState,
                                                primaryjoin=( SampleEvent.table.c.sample_state_id == SampleState.table.c.id ) ),

                                ) )
                                
assign_mapper( context, SampleState, SampleState.table,
               properties=None )

assign_mapper( context, UserAddress, UserAddress.table,
               properties=dict( 
                    user=relation( User,
                                   primaryjoin=( UserAddress.table.c.user_id == User.table.c.id ),
                                   backref='addresses',
                                   order_by=desc(UserAddress.table.c.update_time)), 
                ) )


assign_mapper( context, ValidationError, ValidationError.table )

assign_mapper( context, HistoryDatasetAssociation, HistoryDatasetAssociation.table,
    properties=dict( 
        dataset=relation( 
            Dataset, 
            primaryjoin=( Dataset.table.c.id == HistoryDatasetAssociation.table.c.dataset_id ), lazy=False ),
        # .history defined in History mapper
        copied_to_history_dataset_associations=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( HistoryDatasetAssociation.table.c.copied_from_history_dataset_association_id == HistoryDatasetAssociation.table.c.id ),
            backref=backref( "copied_from_history_dataset_association", primaryjoin=( HistoryDatasetAssociation.table.c.copied_from_history_dataset_association_id == HistoryDatasetAssociation.table.c.id ), remote_side=[HistoryDatasetAssociation.table.c.id], uselist=False ) ),
        copied_to_library_dataset_dataset_associations=relation( 
            LibraryDatasetDatasetAssociation, 
            primaryjoin=( HistoryDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ),
            backref=backref( "copied_from_history_dataset_association", primaryjoin=( HistoryDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ), remote_side=[LibraryDatasetDatasetAssociation.table.c.id], uselist=False ) ),
        implicitly_converted_datasets=relation( 
            ImplicitlyConvertedDatasetAssociation, 
            primaryjoin=( ImplicitlyConvertedDatasetAssociation.table.c.hda_parent_id == HistoryDatasetAssociation.table.c.id ) ),
        children=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( HistoryDatasetAssociation.table.c.parent_id == HistoryDatasetAssociation.table.c.id ),
            backref=backref( "parent", primaryjoin=( HistoryDatasetAssociation.table.c.parent_id == HistoryDatasetAssociation.table.c.id ), remote_side=[HistoryDatasetAssociation.table.c.id], uselist=False ) ),
        visible_children=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( ( HistoryDatasetAssociation.table.c.parent_id == HistoryDatasetAssociation.table.c.id ) & ( HistoryDatasetAssociation.table.c.visible == True ) ) ),
        tags=relation(HistoryDatasetAssociationTagAssociation, order_by=HistoryDatasetAssociationTagAssociation.table.c.id, backref='history_tag_associations')
            ) )

assign_mapper( context, Dataset, Dataset.table,
    properties=dict( 
        history_associations=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( Dataset.table.c.id == HistoryDatasetAssociation.table.c.dataset_id ) ),
        active_history_associations=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( ( Dataset.table.c.id == HistoryDatasetAssociation.table.c.dataset_id ) & ( HistoryDatasetAssociation.table.c.deleted == False ) ) ),
        library_associations=relation( 
            LibraryDatasetDatasetAssociation, 
            primaryjoin=( Dataset.table.c.id == LibraryDatasetDatasetAssociation.table.c.dataset_id ) ),
        active_library_associations=relation( 
            LibraryDatasetDatasetAssociation, 
            primaryjoin=( ( Dataset.table.c.id == LibraryDatasetDatasetAssociation.table.c.dataset_id ) & ( LibraryDatasetDatasetAssociation.table.c.deleted == False ) ) ),
        tags=relation(DatasetTagAssociation, order_by=DatasetTagAssociation.table.c.id, backref='datasets')
            ) )

assign_mapper( context, HistoryDatasetAssociationDisplayAtAuthorization, HistoryDatasetAssociationDisplayAtAuthorization.table,
    properties=dict( history_dataset_association = relation( HistoryDatasetAssociation ),
                     user = relation( User ) ) )

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
                     active_datasets=relation( HistoryDatasetAssociation, primaryjoin=( ( HistoryDatasetAssociation.table.c.history_id == History.table.c.id ) & ( not_( HistoryDatasetAssociation.table.c.deleted ) ) ), order_by=asc( HistoryDatasetAssociation.table.c.hid ), viewonly=True ),
                     tags=relation(HistoryTagAssociation, order_by=HistoryTagAssociation.table.c.id, backref="histories") 
                      ) )

assign_mapper( context, HistoryUserShareAssociation, HistoryUserShareAssociation.table,
    properties=dict( user=relation( User, backref='histories_shared_by_others' ),
                     history=relation( History, backref='users_shared_with' )
                   ) )

assign_mapper( context, User, User.table, 
    properties=dict( histories=relation( History, backref="user",
                                         order_by=desc(History.table.c.update_time) ),               
                     active_histories=relation( History, primaryjoin=( ( History.table.c.user_id == User.table.c.id ) & ( not_( History.table.c.deleted ) ) ), order_by=desc( History.table.c.update_time ) ),
                     galaxy_sessions=relation( GalaxySession, order_by=desc( GalaxySession.table.c.update_time ) ),
                     stored_workflow_menu_entries=relation( StoredWorkflowMenuEntry, backref="user",
                                                            cascade="all, delete-orphan",
                                                            collection_class=ordering_list( 'order_index' ) ),
                     preferences=relation( UserPreference, backref="user", order_by=UserPreference.table.c.id),
#                     addresses=relation( UserAddress,
#                                         primaryjoin=( User.table.c.id == UserAddress.table.c.user_id ) )
                     ) )

assign_mapper( context, Group, Group.table,
    properties=dict( users=relation( UserGroupAssociation ) ) )

assign_mapper( context, UserGroupAssociation, UserGroupAssociation.table,
    properties=dict( user=relation( User, backref = "groups" ),
                     group=relation( Group, backref = "members" ) ) )

assign_mapper( context, DefaultUserPermissions, DefaultUserPermissions.table,
    properties=dict( user=relation( User, backref = "default_permissions" ),
                     role=relation( Role ) ) )

assign_mapper( context, DefaultHistoryPermissions, DefaultHistoryPermissions.table,
    properties=dict( history=relation( History, backref = "default_permissions" ),
                     role=relation( Role ) ) )

assign_mapper( context, Role, Role.table,
    properties=dict(
        users=relation( UserRoleAssociation ),
        groups=relation( GroupRoleAssociation )
    )
)

assign_mapper( context, UserRoleAssociation, UserRoleAssociation.table,
    properties=dict(
        user=relation( User, backref="roles" ),
        non_private_roles=relation( User, 
                                    backref="non_private_roles",
                                    primaryjoin=( ( User.table.c.id == UserRoleAssociation.table.c.user_id ) & ( UserRoleAssociation.table.c.role_id == Role.table.c.id ) & not_( Role.table.c.name == User.table.c.email & Role.table.c.type == 'private' ) ) ),
        role=relation( Role )
    )
)

assign_mapper( context, GroupRoleAssociation, GroupRoleAssociation.table,
    properties=dict(
        group=relation( Group, backref="roles" ),
        role=relation( Role )
    )
)

assign_mapper( context, DatasetPermissions, DatasetPermissions.table,
    properties=dict(
        dataset=relation( Dataset, backref="actions" ),
        role=relation( Role, backref="dataset_actions" )
    )
)

assign_mapper( context, LibraryPermissions, LibraryPermissions.table,
    properties=dict(
        library=relation( Library, backref="actions" ),
        role=relation( Role, backref="library_actions" )
    )
)

assign_mapper( context, LibraryFolderPermissions, LibraryFolderPermissions.table,
    properties=dict(
        folder=relation( LibraryFolder, backref="actions" ),
        role=relation( Role, backref="library_folder_actions" )
    )
)

assign_mapper( context, LibraryDatasetPermissions, LibraryDatasetPermissions.table,
    properties=dict(
        library_dataset=relation( LibraryDataset, backref="actions" ),
        role=relation( Role, backref="library_dataset_actions" )
    )
)

assign_mapper( context, LibraryDatasetDatasetAssociationPermissions, LibraryDatasetDatasetAssociationPermissions.table,
    properties=dict(
        library_dataset_dataset_association = relation( LibraryDatasetDatasetAssociation, backref="actions" ),
        role=relation( Role, backref="library_dataset_dataset_actions" )
    )
)

assign_mapper( context, Library, Library.table,
    properties=dict(
        root_folder=relation( LibraryFolder, backref=backref( "library_root" ) )
        )
)

assign_mapper( context, LibraryInfoAssociation, LibraryInfoAssociation.table,
               properties=dict( library=relation( Library,
                                                  primaryjoin=( LibraryInfoAssociation.table.c.library_id == Library.table.c.id ), backref="info_association" ),
                                template=relation( FormDefinition,
                                                   primaryjoin=( LibraryInfoAssociation.table.c.form_definition_id == FormDefinition.table.c.id ) ), 
                                info=relation( FormValues,
                                               primaryjoin=( LibraryInfoAssociation.table.c.form_values_id == FormValues.table.c.id ) )
                              ) )

assign_mapper( context, LibraryFolder, LibraryFolder.table,
    properties=dict( 
        folders=relation( 
            LibraryFolder, 
            primaryjoin=( LibraryFolder.table.c.parent_id == LibraryFolder.table.c.id ),
            order_by=asc( LibraryFolder.table.c.name ),
            backref=backref( "parent", primaryjoin=( LibraryFolder.table.c.parent_id == LibraryFolder.table.c.id ), remote_side=[LibraryFolder.table.c.id] ) ),
        active_folders=relation( LibraryFolder, 
            primaryjoin=( ( LibraryFolder.table.c.parent_id == LibraryFolder.table.c.id ) & ( not_( LibraryFolder.table.c.deleted ) ) ), 
            order_by=asc( LibraryFolder.table.c.name ), 
            lazy=True, #"""sqlalchemy.exceptions.ArgumentError: Error creating eager relationship 'active_folders' on parent class '<class 'galaxy.model.LibraryFolder'>' to child class '<class 'galaxy.model.LibraryFolder'>': Cant use eager loading on a self referential relationship."""
            viewonly=True ),
        datasets=relation( LibraryDataset,
            primaryjoin=( ( LibraryDataset.table.c.folder_id == LibraryFolder.table.c.id ) ), 
            order_by=asc( LibraryDataset.table.c._name ), 
            lazy=False, 
            viewonly=True )
    ) )

assign_mapper( context, LibraryFolderInfoAssociation, LibraryFolderInfoAssociation.table,
               properties=dict( folder=relation( LibraryFolder,
                                                 primaryjoin=( LibraryFolderInfoAssociation.table.c.library_folder_id == LibraryFolder.table.c.id ), backref="info_association" ),
                                template=relation( FormDefinition,
                                                   primaryjoin=( LibraryFolderInfoAssociation.table.c.form_definition_id == FormDefinition.table.c.id ) ), 
                                info=relation( FormValues,
                                               primaryjoin=( LibraryFolderInfoAssociation.table.c.form_values_id == FormValues.table.c.id ) )
                              ) )

assign_mapper( context, LibraryDataset, LibraryDataset.table,
    properties=dict( 
        folder=relation( LibraryFolder ),
        library_dataset_dataset_association=relation( LibraryDatasetDatasetAssociation, primaryjoin=( LibraryDataset.table.c.library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ) ),
        expired_datasets = relation( LibraryDatasetDatasetAssociation, foreign_keys=[LibraryDataset.table.c.id,LibraryDataset.table.c.library_dataset_dataset_association_id ], primaryjoin=( ( LibraryDataset.table.c.id == LibraryDatasetDatasetAssociation.table.c.library_dataset_id ) & ( not_( LibraryDataset.table.c.library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ) ) ), viewonly=True, uselist=True )
        ) )

assign_mapper( context, LibraryDatasetDatasetAssociation, LibraryDatasetDatasetAssociation.table,
    properties=dict( 
        dataset=relation( Dataset ),
        library_dataset = relation( LibraryDataset,
        primaryjoin=( LibraryDatasetDatasetAssociation.table.c.library_dataset_id == LibraryDataset.table.c.id ) ),
        user=relation( User.mapper ),
        copied_to_library_dataset_dataset_associations=relation( 
            LibraryDatasetDatasetAssociation, 
            primaryjoin=( LibraryDatasetDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ),
            backref=backref( "copied_from_library_dataset_dataset_association", primaryjoin=( LibraryDatasetDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ), remote_side=[LibraryDatasetDatasetAssociation.table.c.id] ) ),
        copied_to_history_dataset_associations=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( HistoryDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ),
            backref=backref( "copied_from_library_dataset_dataset_association", primaryjoin=( HistoryDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ), remote_side=[LibraryDatasetDatasetAssociation.table.c.id], uselist=False ) ),
        children=relation( 
            LibraryDatasetDatasetAssociation, 
            primaryjoin=( LibraryDatasetDatasetAssociation.table.c.parent_id == LibraryDatasetDatasetAssociation.table.c.id ),
            backref=backref( "parent", primaryjoin=( LibraryDatasetDatasetAssociation.table.c.parent_id == LibraryDatasetDatasetAssociation.table.c.id ), remote_side=[LibraryDatasetDatasetAssociation.table.c.id] ) ),
        visible_children=relation( 
            LibraryDatasetDatasetAssociation, 
            primaryjoin=( ( LibraryDatasetDatasetAssociation.table.c.parent_id == LibraryDatasetDatasetAssociation.table.c.id ) & ( LibraryDatasetDatasetAssociation.table.c.visible == True ) ) )
        ) )

assign_mapper( context, LibraryDatasetDatasetInfoAssociation, LibraryDatasetDatasetInfoAssociation.table,
               properties=dict( library_dataset_dataset_association=relation( LibraryDatasetDatasetAssociation,
                                                                              primaryjoin=( LibraryDatasetDatasetInfoAssociation.table.c.library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ), backref="info_association" ),
                                template=relation( FormDefinition,
                                                   primaryjoin=( LibraryDatasetDatasetInfoAssociation.table.c.form_definition_id == FormDefinition.table.c.id ) ), 
                                info=relation( FormValues,
                                               primaryjoin=( LibraryDatasetDatasetInfoAssociation.table.c.form_values_id == FormValues.table.c.id ) )
                              ) )

assign_mapper( context, JobToInputDatasetAssociation, JobToInputDatasetAssociation.table,
    properties=dict( job=relation( Job ), dataset=relation( HistoryDatasetAssociation, lazy=False ) ) )

assign_mapper( context, JobToOutputDatasetAssociation, JobToOutputDatasetAssociation.table,
    properties=dict( job=relation( Job ), dataset=relation( HistoryDatasetAssociation, lazy=False ) ) )

assign_mapper( context, JobToOutputLibraryDatasetAssociation, JobToOutputLibraryDatasetAssociation.table,
    properties=dict( job=relation( Job ), dataset=relation( LibraryDatasetDatasetAssociation, lazy=False ) ) )

assign_mapper( context, JobParameter, JobParameter.table )

assign_mapper( context, JobExternalOutputMetadata, JobExternalOutputMetadata.table,
    properties=dict( job = relation( Job ), 
                     history_dataset_association = relation( HistoryDatasetAssociation, lazy = False ),
                     library_dataset_dataset_association = relation( LibraryDatasetDatasetAssociation, lazy = False ) ) )

assign_mapper( context, Job, Job.table, 
    properties=dict( galaxy_session=relation( GalaxySession ),
                     history=relation( History ),
                     library_folder=relation( LibraryFolder ),
                     parameters=relation( JobParameter, lazy=False ),
                     input_datasets=relation( JobToInputDatasetAssociation, lazy=False ),
                     output_datasets=relation( JobToOutputDatasetAssociation, lazy=False ),
                     output_library_datasets=relation( JobToOutputLibraryDatasetAssociation, lazy=False ),
                     external_output_metadata = relation( JobExternalOutputMetadata, lazy = False ) ) )

assign_mapper( context, Event, Event.table,
    properties=dict( history=relation( History ),
                     galaxy_session=relation( GalaxySession ),
                     user=relation( User.mapper ) ) )

assign_mapper( context, GalaxySession, GalaxySession.table,
    properties=dict( histories=relation( GalaxySessionToHistoryAssociation ),
                     current_history=relation( History ),
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
                     stored_workflow=relation( StoredWorkflow, backref='users_shared_with' )
                   ) )

assign_mapper( context, StoredWorkflowMenuEntry, StoredWorkflowMenuEntry.table,
    properties=dict( stored_workflow=relation( StoredWorkflow ) ) )

assign_mapper( context, MetadataFile, MetadataFile.table,
    properties=dict( history_dataset=relation( HistoryDatasetAssociation ), library_dataset=relation( LibraryDatasetDatasetAssociation ) ) )

assign_mapper( context, PageRevision, PageRevision.table )

assign_mapper( context, Page, Page.table,
    properties=dict( user=relation( User ),
                     revisions=relation( PageRevision, backref='page',
                                         cascade="all, delete-orphan",
                                         primaryjoin=( Page.table.c.id == PageRevision.table.c.page_id ) ),
                     latest_revision=relation( PageRevision, post_update=True,
                                               primaryjoin=( Page.table.c.latest_revision_id == PageRevision.table.c.id ),
                                               lazy=False ),
                     tags=relation(PageTagAssociation, order_by=PageTagAssociation.table.c.id, backref="pages") 
                   ) )

assign_mapper( context, Tag, Tag.table,
    properties=dict( children=relation(Tag, backref=backref( 'parent', remote_side=[Tag.table.c.id] ) )  
                     ) )

assign_mapper( context, HistoryTagAssociation, HistoryTagAssociation.table,
    properties=dict( tag=relation(Tag, backref="tagged_histories") ),
                     primary_key=[HistoryTagAssociation.table.c.history_id, HistoryTagAssociation.table.c.tag_id]
                     )

assign_mapper( context, DatasetTagAssociation, DatasetTagAssociation.table,
    properties=dict( tag=relation(Tag, backref="tagged_datasets") ),
                     primary_key=[DatasetTagAssociation.table.c.dataset_id, DatasetTagAssociation.table.c.tag_id]
                     )

assign_mapper( context, HistoryDatasetAssociationTagAssociation, HistoryDatasetAssociationTagAssociation.table,
    properties=dict( tag=relation(Tag, backref="tagged_history_dataset_associations") ),
                     primary_key=[HistoryDatasetAssociationTagAssociation.table.c.history_dataset_association_id, HistoryDatasetAssociationTagAssociation.table.c.tag_id]
                     )

assign_mapper( context, PageTagAssociation, PageTagAssociation.table,
    properties=dict( tag=relation(Tag, backref="tagged_pages") ),
                     primary_key=[PageTagAssociation.table.c.page_id, PageTagAssociation.table.c.tag_id]
               )
               
assign_mapper( context, UserPreference, UserPreference.table, 
    properties = {}
              )

def db_next_hid( self ):
    """
    Override __next_hid to generate from the database in a concurrency
    safe way.
    """
    conn = object_session( self ).connection()
    table = self.table
    trans = conn.begin()
    try:
        next_hid = select( [table.c.hid_counter], table.c.id == self.id, for_update=True ).scalar()
        table.update( table.c.id == self.id ).execute( hid_counter = ( next_hid + 1 ) )
        trans.commit()
        return next_hid
    except:
        trans.rollback()
        raise

History._next_hid = db_next_hid

def guess_dialect_for_url( url ):
    return (url.split(':', 1))[0]

def load_egg_for_url( url ):
    # Load the appropriate db module
    dialect = guess_dialect_for_url( url )
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

def init( file_path, url, engine_options={}, create_tables=False ):
    """Connect mappings to the database"""
    # Connect dataset to the file path
    Dataset.file_path = file_path
    # Load the appropriate db module
    load_egg_for_url( url )
    # Create the database engine
    engine = create_engine( url, **engine_options )
    # Connect the metadata to the database.
    metadata.bind = engine
    # Clear any existing contextual sessions and reconfigure
    Session.remove()
    Session.configure( bind=engine )
    # Create tables if needed
    if create_tables:
        metadata.create_all()
        # metadata.engine.commit()
    # Pack everything into a bunch
    result = Bunch( **globals() )
    result.engine = engine
    result.flush = lambda *args, **kwargs: Session.flush( *args, **kwargs )
    result.session = Session
    # For backward compatibility with "model.context.current"
    result.context = Session
    result.create_tables = create_tables
    #load local galaxy security policy
    result.security_agent = GalaxyRBACAgent( result )
    return result
    
def get_suite():
    """Get unittest suite for this module"""
    import unittest, mapping_tests
    return unittest.makeSuite( mapping_tests.MappingTests )

