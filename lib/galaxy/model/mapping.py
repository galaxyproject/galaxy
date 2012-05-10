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
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.ext.associationproxy import association_proxy

metadata = MetaData()
context = Session = scoped_session( sessionmaker( autoflush=False, autocommit=True ) )

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
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ),
    Column( "disk_usage", Numeric( 15, 0 ), index=True ) )

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

UserOpenID.table = Table( "galaxy_user_openid", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "openid", TEXT, index=True, unique=True ),
    Column( "provider", TrimmedString( 255 ) ),
    )

History.table = Table( "history", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "name", TrimmedString( 255 ) ),
    Column( "hid_counter", Integer, default=1 ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ),
    Column( "importing", Boolean, index=True, default=False ),
    Column( "genome_build", TrimmedString( 40 ) ),
    Column( "importable", Boolean, default=False ),
    Column( "slug", TEXT, index=True ),
    Column( "published", Boolean, index=True, default=False ) )

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
    Column( "state", TrimmedString( 64 ), index=True, key="_state" ),
    Column( "copied_from_history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), nullable=True ),
    Column( "copied_from_library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), nullable=True ),
    Column( "hid", Integer ),
    Column( "name", TrimmedString( 255 ) ),
    Column( "info", TrimmedString( 255 ) ),
    Column( "blurb", TrimmedString( 255 ) ),
    Column( "peek" , TEXT ),
    Column( "tool_version" , TEXT ),
    Column( "extension", TrimmedString( 64 ) ),
    Column( "metadata", MetadataType(), key="_metadata" ),
    Column( "parent_id", Integer, ForeignKey( "history_dataset_association.id" ), nullable=True ),
    Column( "designation", TrimmedString( 255 ) ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ),
    Column( "visible", Boolean ) )

Dataset.table = Table( "dataset", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "state", TrimmedString( 64 ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ),
    Column( "purgable", Boolean, default=True ),
    Column( "object_store_id", TrimmedString( 255 ), index=True ),
    Column( "external_filename" , TEXT ),
    Column( "_extra_files_path", TEXT ),
    Column( 'file_size', Numeric( 15, 0 ) ),
    Column( 'total_size', Numeric( 15, 0 ) ) )

HistoryDatasetAssociationDisplayAtAuthorization.table = Table( "history_dataset_association_display_at_authorization", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "site", TrimmedString( 255 ) ) )
    
HistoryDatasetAssociationSubset.table = Table( "history_dataset_association_subset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "history_dataset_association_subset_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "location", Unicode(255), index=True) )

ImplicitlyConvertedDatasetAssociation.table = Table( "implicitly_converted_dataset_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "hda_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True, nullable=True ),
    Column( "ldda_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), index=True, nullable=True ),
    Column( "hda_parent_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "ldda_parent_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), index=True ),
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

UserQuotaAssociation.table = Table( "user_quota_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "quota_id", Integer, ForeignKey( "quota.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

GroupQuotaAssociation.table = Table( "group_quota_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "group_id", Integer, ForeignKey( "galaxy_group.id" ), index=True ),
    Column( "quota_id", Integer, ForeignKey( "quota.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

Quota.table = Table( "quota", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", String( 255 ), index=True, unique=True ),
    Column( "description", TEXT ),
    Column( "bytes", BigInteger ),
    Column( "operation", String( 8 ) ),
    Column( "deleted", Boolean, index=True, default=False ) )

DefaultQuotaAssociation.table = Table( "default_quota_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "type", String( 32 ), index=True, unique=True ),
    Column( "quota_id", Integer, ForeignKey( "quota.id" ), index=True ) )

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
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ) )

LibraryDatasetDatasetAssociation.table = Table( "library_dataset_dataset_association", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "library_dataset_id", Integer, ForeignKey( "library_dataset.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "state", TrimmedString( 64 ), index=True, key="_state" ),
    Column( "copied_from_history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id", use_alter=True, name='history_dataset_association_dataset_id_fkey' ), nullable=True ),
    Column( "copied_from_library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id", use_alter=True, name='library_dataset_dataset_association_id_fkey' ), nullable=True ),
    Column( "name", TrimmedString( 255 ), index=True ),
    Column( "info", TrimmedString( 255 ) ),
    Column( "blurb", TrimmedString( 255 ) ),
    Column( "peek" , TEXT ),
    Column( "tool_version" , TEXT ),
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
    Column( "description", TEXT ),
    Column( "synopsis", TEXT ) )

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
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
    Column( "inheritable", Boolean, index=True, default=False ),
    Column( "deleted", Boolean, index=True, default=False ) )

LibraryFolderInfoAssociation.table = Table( 'library_folder_info_association', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "library_folder_id", Integer, ForeignKey( "library_folder.id" ), nullable=True, index=True ),
    Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
    Column( "inheritable", Boolean, index=True, default=False ),
    Column( "deleted", Boolean, index=True, default=False ) )

LibraryDatasetDatasetInfoAssociation.table = Table( 'library_dataset_dataset_info_association', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), nullable=True, index=True ),
    Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

ToolShedRepository.table = Table( "tool_shed_repository", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "tool_shed", TrimmedString( 255 ), index=True ),
    Column( "name", TrimmedString( 255 ), index=True ),
    Column( "description" , TEXT ),
    Column( "owner", TrimmedString( 255 ), index=True ),
    Column( "installed_changeset_revision", TrimmedString( 255 ) ),
    Column( "changeset_revision", TrimmedString( 255 ), index=True ),
    Column( "ctx_rev", TrimmedString( 10 ) ),
    Column( "metadata", JSONType, nullable=True ),
    Column( "includes_datatypes", Boolean, index=True, default=False ),
    Column( "update_available", Boolean, default=False ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "uninstalled", Boolean, default=False ),
    Column( "dist_to_shed", Boolean, default=False ) )

ToolVersion.table = Table( "tool_version", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "tool_id", String( 255 ) ),
    Column( "tool_shed_repository_id", Integer, ForeignKey( "tool_shed_repository.id" ), index=True, nullable=True ) )

ToolVersionAssociation.table = Table( "tool_version_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "tool_id", Integer, ForeignKey( "tool_version.id" ), index=True, nullable=False ),
    Column( "parent_id", Integer, ForeignKey( "tool_version.id" ), index=True, nullable=False ) )

MigrateTools.table = Table( "migrate_tools", metadata,
    Column( "repository_id", TrimmedString( 255 ) ),
    Column( "repository_path", TEXT ),
    Column( "version", Integer ) )

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
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=True ),
    Column( "job_runner_name", String( 255 ) ),
    Column( "job_runner_external_id", String( 255 ) ), 
    Column( "object_store_id", TrimmedString( 255 ), index=True ),
    Column( "imported", Boolean, default=False, index=True ),
    Column( "params", TrimmedString(255), index=True ),
    Column( "handler", TrimmedString( 255 ), index=True ) )
    
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
    
JobToInputLibraryDatasetAssociation.table = Table( "job_to_input_library_dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "ldda_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), index=True ),
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
    Column( "filename_override_metadata", String( 255 ) ),
    Column( "job_runner_external_pid", String( 255 ) ) )
    
JobExportHistoryArchive.table = Table( "job_export_history_archive", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "compressed", Boolean, index=True, default=False ),
    Column( "history_attrs_filename", TEXT ),
    Column( "datasets_attrs_filename", TEXT ),
    Column( "jobs_attrs_filename", TEXT )
    )
    
JobImportHistoryArchive.table = Table( "job_import_history_archive", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "archive_dir", TEXT )
    )

GenomeIndexToolData.table = Table( "genome_index_tool_data", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "deferred_job_id", Integer, ForeignKey( "deferred_job.id" ), index=True ),
    Column( "transfer_job_id", Integer, ForeignKey( "transfer_job.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "fasta_path", String( 255 ) ),
    Column( "created_time", DateTime, default=now ),
    Column( "modified_time", DateTime, default=now, onupdate=now ),
    Column( "indexer", String( 64 ) ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    )
    
Task.table = Table( "task", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "execution_time", DateTime ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "state", String( 64 ), index=True ),
    Column( "command_line", TEXT ), 
    Column( "param_filename", String( 1024 ) ),
    Column( "runner_name", String( 255 ) ),
    Column( "stdout", TEXT ),
    Column( "stderr", TEXT ),
    Column( "info", TrimmedString ( 255 ) ),
    Column( "traceback", TEXT ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True, nullable=False ),
    Column( "working_directory", String(1024)),
    Column( "task_runner_name", String( 255 ) ),
    Column( "task_runner_external_id", String( 255 ) ),
    Column( "prepare_input_files_cmd", TEXT ) )

PostJobAction.table = Table("post_job_action", metadata,
    Column("id", Integer, primary_key=True),
    Column("workflow_step_id", Integer, ForeignKey( "workflow_step.id" ), index=True, nullable=False),
    Column("action_type", String(255), nullable=False),
    Column("output_name", String(255), nullable=True),
    Column("action_arguments", JSONType, nullable=True))

PostJobActionAssociation.table = Table("post_job_action_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("job_id", Integer, ForeignKey( "job.id" ), index=True, nullable=False),
    Column("post_job_action_id", Integer, ForeignKey( "post_job_action.id" ), index=True, nullable=False))

DeferredJob.table = Table( "deferred_job", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "state", String( 64 ), index=True ),
    Column( "plugin", String( 128 ), index=True ),
    Column( "params", JSONType ) )

TransferJob.table = Table( "transfer_job", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "state", String( 64 ), index=True ),
    Column( "path", String( 1024 ) ),
    Column( "info", TEXT ),
    Column( "pid", Integer ),
    Column( "socket", Integer ),
    Column( "params", JSONType ) )

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
    Column( "prev_session_id", Integer ), # saves a reference to the previous session so we have a way to chain them together
    Column( "disk_usage", Numeric( 15, 0 ), index=True ) )

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
    Column( "slug", TEXT, index=True ),
    Column( "published", Boolean, index=True, default=False )
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

WorkflowOutput.table = Table( "workflow_output", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "workflow_step_id", Integer, ForeignKey("workflow_step.id"), index=True, nullable=False),
    Column( "output_name", String(255), nullable=True)
    )

WorkflowInvocation.table = Table( "workflow_invocation", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "workflow_id", Integer, ForeignKey( "workflow.id" ), index=True, nullable=False )
    )

WorkflowInvocationStep.table = Table( "workflow_invocation_step", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "workflow_invocation_id", Integer, ForeignKey( "workflow_invocation.id" ), index=True, nullable=False ),
    Column( "workflow_step_id",  Integer, ForeignKey( "workflow_step.id" ), index=True, nullable=False ),
    Column( "job_id",  Integer, ForeignKey( "job.id" ), index=True, nullable=True )
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
    Column( "object_store_id", TrimmedString( 255 ), index=True ),
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

ExternalService.table = Table( 'external_service', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), nullable=False ),
    Column( "description", TEXT ),
    Column( "external_service_type_id", TrimmedString( 255 ), nullable=False ),
    Column( "version", TrimmedString( 255 ) ),
    Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

RequestType.table = Table('request_type', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), nullable=False ),
    Column( "desc", TEXT ),
    Column( "request_form_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "sample_form_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

RequestTypeExternalServiceAssociation.table = Table( "request_type_external_service_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "request_type_id", Integer, ForeignKey( "request_type.id" ), index=True ),
    Column( "external_service_id", Integer, ForeignKey( "external_service.id" ), index=True ) )

RequestTypePermissions.table = Table( "request_type_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "request_type_id", Integer, ForeignKey( "request_type.id" ), nullable=True, index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

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
    Column( "notification", JSONType() ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
    Column( "request_type_id", Integer, ForeignKey( "request_type.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

RequestEvent.table = Table('request_event', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "request_id", Integer, ForeignKey( "request.id" ), index=True ), 
    Column( "state", TrimmedString( 255 ),  index=True ),
    Column( "comment", TEXT ) )

Sample.table = Table('sample', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), nullable=False ),
    Column( "desc", TEXT ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
    Column( "request_id", Integer, ForeignKey( "request.id" ), index=True ),
    Column( "bar_code", TrimmedString( 255 ), index=True ),
    Column( "library_id", Integer, ForeignKey( "library.id" ), index=True ),
    Column( "folder_id", Integer, ForeignKey( "library_folder.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "workflow", JSONType, nullable=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), nullable=True) )

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

SampleDataset.table = Table('sample_dataset', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "sample_id", Integer, ForeignKey( "sample.id" ), index=True ), 
    Column( "name", TrimmedString( 255 ), nullable=False ),
    Column( "file_path", TEXT ),
    Column( "status", TrimmedString( 255 ), nullable=False ),
    Column( "error_msg", TEXT ),
    Column( "size", TrimmedString( 255 ) ),
    Column( "external_service_id", Integer, ForeignKey( "external_service.id" ), index=True ) ) 

Run.table = Table( 'run', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "subindex", TrimmedString( 255 ), index=True ) )

RequestTypeRunAssociation.table = Table( "request_type_run_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "request_type_id", Integer, ForeignKey( "request_type.id" ), index=True, nullable=False ),
    Column( "run_id", Integer, ForeignKey( "run.id" ), index=True, nullable=False ) )

SampleRunAssociation.table = Table( "sample_run_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "sample_id", Integer, ForeignKey( "sample.id" ), index=True, nullable=False ),
    Column( "run_id", Integer, ForeignKey( "run.id" ), index=True, nullable=False ) )

Page.table = Table( "page", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
    Column( "latest_revision_id", Integer,
            ForeignKey( "page_revision.id", use_alter=True, name='page_latest_revision_id_fk' ), index=True ),
    Column( "title", TEXT ),
    Column( "slug", TEXT, unique=True, index=True ),
    Column( "importable", Boolean, index=True, default=False ), 
    Column( "published", Boolean, index=True, default=False ), 
    Column( "deleted", Boolean, index=True, default=False ), 
    )

PageRevision.table = Table( "page_revision", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True, nullable=False ),
    Column( "title", TEXT ),
    Column( "content", TEXT )
    )

PageUserShareAssociation.table = Table( "page_user_share_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True )
    )

Visualization.table = Table( "visualization", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
    Column( "latest_revision_id", Integer,
            ForeignKey( "visualization_revision.id", use_alter=True, name='visualization_latest_revision_id_fk' ), index=True ),
    Column( "title", TEXT ),
    Column( "type", TEXT ),
    Column( "dbkey", TEXT, index=True ),
    Column( "deleted", Boolean, default=False, index=True ),
    Column( "importable", Boolean, default=False, index=True ),
    Column( "slug", TEXT, index=True ),
    Column( "published", Boolean, default=False, index=True )
    )

VisualizationRevision.table = Table( "visualization_revision", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "visualization_id", Integer, ForeignKey( "visualization.id" ), index=True, nullable=False ),
    Column( "title", TEXT ),
    Column( "dbkey", TEXT, index=True ),
    Column( "config", JSONType )
    )
    
VisualizationUserShareAssociation.table = Table( "visualization_user_share_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "visualization_id", Integer, ForeignKey( "visualization.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True )
    )
    
# Tagging tables.

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
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )
    
DatasetTagAssociation.table = Table( "dataset_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

HistoryDatasetAssociationTagAssociation.table = Table( "history_dataset_association_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )
        
StoredWorkflowTagAssociation.table = Table( "stored_workflow_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", Unicode(255), index=True),
    Column( "value", Unicode(255), index=True),
    Column( "user_value", Unicode(255), index=True) )

PageTagAssociation.table = Table( "page_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )
    
WorkflowStepTagAssociation.table = Table( "workflow_step_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "workflow_step_id", Integer, ForeignKey( "workflow_step.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", Unicode(255), index=True),
    Column( "value", Unicode(255), index=True),
    Column( "user_value", Unicode(255), index=True) )
    
VisualizationTagAssociation.table = Table( "visualization_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "visualization_id", Integer, ForeignKey( "visualization.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )
    
ToolTagAssociation.table = Table( "tool_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "tool_id", TrimmedString(255), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )
 
# Annotation tables.

HistoryAnnotationAssociation.table = Table( "history_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT, index=True) )

HistoryDatasetAssociationAnnotationAssociation.table = Table( "history_dataset_association_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT, index=True) )

StoredWorkflowAnnotationAssociation.table = Table( "stored_workflow_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT, index=True) )

WorkflowStepAnnotationAssociation.table = Table( "workflow_step_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "workflow_step_id", Integer, ForeignKey( "workflow_step.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT, index=True) )
    
PageAnnotationAssociation.table = Table( "page_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT, index=True) )
    
VisualizationAnnotationAssociation.table = Table( "visualization_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "visualization_id", Integer, ForeignKey( "visualization.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT, index=True) )
    
# Ratings tables.
HistoryRatingAssociation.table = Table( "history_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True) )
    
HistoryDatasetAssociationRatingAssociation.table = Table( "history_dataset_association_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True) )
    
StoredWorkflowRatingAssociation.table = Table( "stored_workflow_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True) )
    
PageRatingAssociation.table = Table( "page_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True) )
    
VisualizationRatingAssociation.table = Table( "visualization_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "visualization_id", Integer, ForeignKey( "visualization.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True) )
    
# User tables.
    
UserPreference.table = Table( "user_preference", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "name", Unicode( 255 ), index=True),
    Column( "value", Unicode( 1024 ) ) )
    
UserAction.table = Table( "user_action", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), index=True ),
    Column( "action", Unicode( 255 ) ),
    Column( "context", Unicode( 512 ) ),
    Column( "params", Unicode( 1024 ) ) )

APIKeys.table = Table( "api_keys", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "key", TrimmedString( 32 ), index=True, unique=True ) )

# With the tables defined we can define the mappers and setup the 
# relationships between the model objects.

assign_mapper( context, Sample, Sample.table,
               properties=dict( 
                    events=relation( SampleEvent, backref="sample",
                        order_by=desc( SampleEvent.table.c.update_time ) ),
                    datasets=relation( SampleDataset, backref="sample",
                        order_by=desc( SampleDataset.table.c.update_time ) ),
                    values=relation( FormValues,
                        primaryjoin=( Sample.table.c.form_values_id == FormValues.table.c.id ) ),
                    request=relation( Request,
                        primaryjoin=( Sample.table.c.request_id == Request.table.c.id ) ),
                    folder=relation( LibraryFolder,
                        primaryjoin=( Sample.table.c.folder_id == LibraryFolder.table.c.id ) ),                 
                    library=relation( Library,
                        primaryjoin=( Sample.table.c.library_id == Library.table.c.id ) ),
                    history=relation( History,
                        primaryjoin=( Sample.table.c.history_id == History.table.c.id ) ),
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
                                                  primaryjoin=( Request.table.c.id == Sample.table.c.request_id ),
                                                  order_by=asc( Sample.table.c.id ) ),
                                events=relation( RequestEvent, backref="request",
                                                 order_by=desc( RequestEvent.table.c.update_time ) )
                              ) )

assign_mapper( context, RequestEvent, RequestEvent.table,
               properties=None )

assign_mapper( context, ExternalService, ExternalService.table,
               properties=dict( form_definition=relation( FormDefinition,
                                                       primaryjoin=( ExternalService.table.c.form_definition_id == FormDefinition.table.c.id ) ),
                                form_values=relation( FormValues,
                                                      primaryjoin=( ExternalService.table.c.form_values_id == FormValues.table.c.id ) ) 
                                ) )

assign_mapper( context, RequestType, RequestType.table,               
               properties=dict( states=relation( SampleState, 
                                                 backref="request_type",
                                                 primaryjoin=( RequestType.table.c.id == SampleState.table.c.request_type_id ),
                                                 order_by=asc( SampleState.table.c.update_time ) ),
                                request_form=relation( FormDefinition,
                                                       primaryjoin=( RequestType.table.c.request_form_id == FormDefinition.table.c.id ) ),
                                sample_form=relation( FormDefinition,
                                                      primaryjoin=( RequestType.table.c.sample_form_id == FormDefinition.table.c.id ) ),
                              ) )

assign_mapper( context, RequestTypeExternalServiceAssociation, RequestTypeExternalServiceAssociation.table,
    properties=dict(
        request_type=relation( RequestType, 
                               primaryjoin=( ( RequestTypeExternalServiceAssociation.table.c.request_type_id == RequestType.table.c.id ) ), backref="external_service_associations" ),
        external_service=relation( ExternalService,
                                   primaryjoin=( RequestTypeExternalServiceAssociation.table.c.external_service_id == ExternalService.table.c.id ) )
    )
)


assign_mapper( context, RequestTypePermissions, RequestTypePermissions.table,
    properties=dict(
        request_type=relation( RequestType, backref="actions" ),
        role=relation( Role, backref="request_type_actions" )
    )
)

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

assign_mapper( context, SampleDataset, SampleDataset.table,
               properties=dict( external_service=relation( ExternalService,
                                                           primaryjoin=( SampleDataset.table.c.external_service_id == ExternalService.table.c.id ) )
    ) 
)


assign_mapper( context, SampleRunAssociation, SampleRunAssociation.table,
               properties=dict( sample=relation( Sample, backref="runs", order_by=desc( Run.table.c.update_time ) ),
                                run=relation( Run, backref="samples", order_by=asc( Sample.table.c.id ) ) ) )

assign_mapper( context, RequestTypeRunAssociation, RequestTypeRunAssociation.table,
               properties=dict( request_type=relation( RequestType, backref="run" ),
                                run=relation( Run, backref="request_type" ) ) )

assign_mapper( context, Run, Run.table,
                properties=dict( template=relation( FormDefinition,
                                                    primaryjoin=( Run.table.c.form_definition_id == FormDefinition.table.c.id ) ), 
                                 info=relation( FormValues,
                                                primaryjoin=( Run.table.c.form_values_id == FormValues.table.c.id ) ) ) )

assign_mapper( context, UserAddress, UserAddress.table,
               properties=dict( 
                    user=relation( User,
                                   primaryjoin=( UserAddress.table.c.user_id == User.table.c.id ),
                                   backref='addresses',
                                   order_by=desc(UserAddress.table.c.update_time)), 
                ) )

assign_mapper( context, UserOpenID, UserOpenID.table,
    properties=dict( 
        session=relation( GalaxySession,
                          primaryjoin=( UserOpenID.table.c.session_id == GalaxySession.table.c.id ),
                          backref='openids',
                          order_by=desc( UserOpenID.table.c.update_time ) ),
        user=relation( User,
                       primaryjoin=( UserOpenID.table.c.user_id == User.table.c.id ),
                       backref='openids',
                       order_by=desc( UserOpenID.table.c.update_time ) ) ) )


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
        implicitly_converted_parent_datasets=relation( 
            ImplicitlyConvertedDatasetAssociation, 
            primaryjoin=( ImplicitlyConvertedDatasetAssociation.table.c.hda_id == HistoryDatasetAssociation.table.c.id ) ),
        children=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( HistoryDatasetAssociation.table.c.parent_id == HistoryDatasetAssociation.table.c.id ),
            backref=backref( "parent", primaryjoin=( HistoryDatasetAssociation.table.c.parent_id == HistoryDatasetAssociation.table.c.id ), remote_side=[HistoryDatasetAssociation.table.c.id], uselist=False ) ),
        visible_children=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( ( HistoryDatasetAssociation.table.c.parent_id == HistoryDatasetAssociation.table.c.id ) & ( HistoryDatasetAssociation.table.c.visible == True ) ) ),
        tags=relation( HistoryDatasetAssociationTagAssociation, order_by=HistoryDatasetAssociationTagAssociation.table.c.id, backref='history_tag_associations' ),
        annotations=relation( HistoryDatasetAssociationAnnotationAssociation, order_by=HistoryDatasetAssociationAnnotationAssociation.table.c.id, backref="hdas" ),
        ratings=relation( HistoryDatasetAssociationRatingAssociation, order_by=HistoryDatasetAssociationRatingAssociation.table.c.id, backref="hdas" ) )
            )

assign_mapper( context, Dataset, Dataset.table,
    properties=dict( 
        history_associations=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( Dataset.table.c.id == HistoryDatasetAssociation.table.c.dataset_id ) ),
        active_history_associations=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( ( Dataset.table.c.id == HistoryDatasetAssociation.table.c.dataset_id ) & ( HistoryDatasetAssociation.table.c.deleted == False ) & ( HistoryDatasetAssociation.table.c.purged == False ) ) ),
        purged_history_associations=relation(
            HistoryDatasetAssociation,
            primaryjoin=( ( Dataset.table.c.id == HistoryDatasetAssociation.table.c.dataset_id ) & ( HistoryDatasetAssociation.table.c.purged == True ) ) ),
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
                     
assign_mapper( context, HistoryDatasetAssociationSubset, HistoryDatasetAssociationSubset.table,
    properties=dict( hda = relation( HistoryDatasetAssociation,
                        primaryjoin=( HistoryDatasetAssociationSubset.table.c.history_dataset_association_id == HistoryDatasetAssociation.table.c.id ) ),
                     subset = relation( HistoryDatasetAssociation,
                        primaryjoin=( HistoryDatasetAssociationSubset.table.c.history_dataset_association_subset_id == HistoryDatasetAssociation.table.c.id ) )
                    ) )

assign_mapper( context, ImplicitlyConvertedDatasetAssociation, ImplicitlyConvertedDatasetAssociation.table, 
    properties=dict( parent_hda=relation( 
                        HistoryDatasetAssociation, 
                        primaryjoin=( ImplicitlyConvertedDatasetAssociation.table.c.hda_parent_id == HistoryDatasetAssociation.table.c.id ) ),
                     parent_ldda=relation( 
                        LibraryDatasetDatasetAssociation, 
                        primaryjoin=( ImplicitlyConvertedDatasetAssociation.table.c.ldda_parent_id == LibraryDatasetDatasetAssociation.table.c.id ) ),
                     dataset_ldda=relation( 
                        LibraryDatasetDatasetAssociation, 
                        primaryjoin=( ImplicitlyConvertedDatasetAssociation.table.c.ldda_id == LibraryDatasetDatasetAssociation.table.c.id ) ),
                     dataset=relation( 
                        HistoryDatasetAssociation, 
                        primaryjoin=( ImplicitlyConvertedDatasetAssociation.table.c.hda_id == HistoryDatasetAssociation.table.c.id ) ) ) )

assign_mapper( context, History, History.table,
    properties=dict( galaxy_sessions=relation( GalaxySessionToHistoryAssociation ),
                     datasets=relation( HistoryDatasetAssociation, backref="history", order_by=asc(HistoryDatasetAssociation.table.c.hid) ),
                     active_datasets=relation( HistoryDatasetAssociation, primaryjoin=( ( HistoryDatasetAssociation.table.c.history_id == History.table.c.id ) & not_( HistoryDatasetAssociation.table.c.deleted ) ), order_by=asc( HistoryDatasetAssociation.table.c.hid ), viewonly=True ),
                     visible_datasets=relation( HistoryDatasetAssociation, primaryjoin=( ( HistoryDatasetAssociation.table.c.history_id == History.table.c.id ) & not_( HistoryDatasetAssociation.table.c.deleted ) & HistoryDatasetAssociation.table.c.visible ),
                     order_by=asc( HistoryDatasetAssociation.table.c.hid ), viewonly=True ),
                     tags=relation( HistoryTagAssociation, order_by=HistoryTagAssociation.table.c.id, backref="histories" ),
                     annotations=relation( HistoryAnnotationAssociation, order_by=HistoryAnnotationAssociation.table.c.id, backref="histories" ),
                     ratings=relation( HistoryRatingAssociation, order_by=HistoryRatingAssociation.table.c.id, backref="histories" ) )  
                      )

# Set up proxy so that 
#   History.users_shared_with
# returns a list of users that history is shared with.
History.users_shared_with_dot_users = association_proxy( 'users_shared_with', 'user' )

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
                     _preferences=relation( UserPreference, backref="user", collection_class=attribute_mapped_collection('name')),
#                     addresses=relation( UserAddress,
#                                         primaryjoin=( User.table.c.id == UserAddress.table.c.user_id ) )
                     values=relation( FormValues,
                                      primaryjoin=( User.table.c.form_values_id == FormValues.table.c.id ) ),
                     api_keys=relation( APIKeys, backref="user", order_by=desc( APIKeys.table.c.create_time ) ),
                     ) )
                     
# Set up proxy so that this syntax is possible:
# <user_obj>.preferences[pref_name] = pref_value
User.preferences = association_proxy('_preferences', 'value', creator=UserPreference)

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
                                    primaryjoin=( ( User.table.c.id == UserRoleAssociation.table.c.user_id ) & ( UserRoleAssociation.table.c.role_id == Role.table.c.id ) & not_( Role.table.c.name == User.table.c.email ) ) ),
        role=relation( Role )
    )
)

assign_mapper( context, GroupRoleAssociation, GroupRoleAssociation.table,
    properties=dict(
        group=relation( Group, backref="roles" ),
        role=relation( Role )
    )
)

assign_mapper( context, Quota, Quota.table,
    properties=dict( users=relation( UserQuotaAssociation ),
                     groups=relation( GroupQuotaAssociation ) ) )

assign_mapper( context, UserQuotaAssociation, UserQuotaAssociation.table,
    properties=dict( user=relation( User, backref="quotas" ),
                     quota=relation( Quota ) ) )

assign_mapper( context, GroupQuotaAssociation, GroupQuotaAssociation.table,
    properties=dict( group=relation( Group, backref="quotas" ),
                     quota=relation( Quota ) ) )

assign_mapper( context, DefaultQuotaAssociation, DefaultQuotaAssociation.table,
    properties=dict( quota=relation( Quota, backref="default" ) ) )

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
                                                  primaryjoin=( ( LibraryInfoAssociation.table.c.library_id == Library.table.c.id ) & ( not_( LibraryInfoAssociation.table.c.deleted ) ) ), backref="info_association" ),
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
            lazy=True,
            viewonly=True ),
        active_datasets=relation( LibraryDataset,
            primaryjoin=( ( LibraryDataset.table.c.folder_id == LibraryFolder.table.c.id ) & ( not_( LibraryDataset.table.c.deleted ) ) ),
            order_by=asc( LibraryDataset.table.c._name ),
            lazy=True,
            viewonly=True )
    ) )

assign_mapper( context, LibraryFolderInfoAssociation, LibraryFolderInfoAssociation.table,
               properties=dict( folder=relation( LibraryFolder,
                                                 primaryjoin=( ( LibraryFolderInfoAssociation.table.c.library_folder_id == LibraryFolder.table.c.id ) & ( not_( LibraryFolderInfoAssociation.table.c.deleted ) ) ), backref="info_association" ),
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
        implicitly_converted_datasets=relation( 
            ImplicitlyConvertedDatasetAssociation, 
            primaryjoin=( ImplicitlyConvertedDatasetAssociation.table.c.ldda_parent_id == LibraryDatasetDatasetAssociation.table.c.id ) ),
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
                                                                              primaryjoin=( ( LibraryDatasetDatasetInfoAssociation.table.c.library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ) & ( not_( LibraryDatasetDatasetInfoAssociation.table.c.deleted ) ) ), backref="info_association" ),
                                template=relation( FormDefinition,
                                                   primaryjoin=( LibraryDatasetDatasetInfoAssociation.table.c.form_definition_id == FormDefinition.table.c.id ) ), 
                                info=relation( FormValues,
                                               primaryjoin=( LibraryDatasetDatasetInfoAssociation.table.c.form_values_id == FormValues.table.c.id ) )
                              ) )

assign_mapper( context, JobToInputDatasetAssociation, JobToInputDatasetAssociation.table,
    properties=dict( job=relation( Job ), dataset=relation( HistoryDatasetAssociation, lazy=False ) ) )

assign_mapper( context, JobToOutputDatasetAssociation, JobToOutputDatasetAssociation.table,
    properties=dict( job=relation( Job ), dataset=relation( HistoryDatasetAssociation, lazy=False ) ) )

assign_mapper( context, JobToInputLibraryDatasetAssociation, JobToInputLibraryDatasetAssociation.table,
    properties=dict( job=relation( Job ), dataset=relation( LibraryDatasetDatasetAssociation, lazy=False ) ) )

assign_mapper( context, JobToOutputLibraryDatasetAssociation, JobToOutputLibraryDatasetAssociation.table,
    properties=dict( job=relation( Job ), dataset=relation( LibraryDatasetDatasetAssociation, lazy=False ) ) )

assign_mapper( context, JobParameter, JobParameter.table )

assign_mapper( context, JobExternalOutputMetadata, JobExternalOutputMetadata.table,
    properties=dict( job = relation( Job ), 
                     history_dataset_association = relation( HistoryDatasetAssociation, lazy = False ),
                     library_dataset_dataset_association = relation( LibraryDatasetDatasetAssociation, lazy = False ) ) )
                     
assign_mapper( context, JobExportHistoryArchive, JobExportHistoryArchive.table,
    properties=dict( job = relation( Job ),
                     history = relation( History ),
                     dataset = relation( Dataset ) ) )
                     
assign_mapper( context, JobImportHistoryArchive, JobImportHistoryArchive.table,
    properties=dict( job = relation( Job ), history = relation( History ) ) )

assign_mapper( context, GenomeIndexToolData, GenomeIndexToolData.table,
    properties=dict( job = relation( Job ),
                     dataset = relation( Dataset ),
                     user = relation( User ),
                     deferred = relation( DeferredJob, backref='deferred_job' ),
                     transfer = relation( TransferJob, backref='transfer_job' ) ) )
                     
assign_mapper( context, PostJobAction, PostJobAction.table,
    properties=dict(workflow_step = relation( WorkflowStep, backref='post_job_actions', primaryjoin=(WorkflowStep.table.c.id == PostJobAction.table.c.workflow_step_id))))

assign_mapper( context, PostJobActionAssociation, PostJobActionAssociation.table,
    properties=dict( job = relation( Job ), 
                     post_job_action = relation( PostJobAction) ) )

assign_mapper( context, Job, Job.table, 
    properties=dict( user=relation( User.mapper ),
                     galaxy_session=relation( GalaxySession ),
                     history=relation( History ),
                     library_folder=relation( LibraryFolder ),
                     parameters=relation( JobParameter, lazy=False ),
                     input_datasets=relation( JobToInputDatasetAssociation ),
                     output_datasets=relation( JobToOutputDatasetAssociation ),
                     post_job_actions=relation( PostJobActionAssociation, lazy=False ),
                     input_library_datasets=relation( JobToInputLibraryDatasetAssociation ),
                     output_library_datasets=relation( JobToOutputLibraryDatasetAssociation ),
                     external_output_metadata = relation( JobExternalOutputMetadata, lazy = False ) ) )

assign_mapper( context, Task, Task.table,
    properties=dict( job = relation( Job )))
                     
assign_mapper( context, DeferredJob, DeferredJob.table, 
    properties = {} )

assign_mapper( context, TransferJob, TransferJob.table, 
    properties = {} )
    
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
LibraryDatasetDatasetAssociation.mapper.add_property( "creating_job_associations", relation( JobToOutputLibraryDatasetAssociation ) )

assign_mapper( context, Workflow, Workflow.table,
    properties=dict( steps=relation( WorkflowStep, backref='workflow',
                                     order_by=asc(WorkflowStep.table.c.order_index),
                                     cascade="all, delete-orphan",
                                     lazy=False ),
                     # outputs = relation( WorkflowOutput, backref='workflow',
                     #                 primaryjoin=(Workflow.table.c.id == WorkflowStep.table.c.workflow_id),
                     #                 secondaryjoin=(WorkflowStep.table.c.id == WorkflowOutput.table.c.workflow_step_id))
                                      ) )

assign_mapper( context, WorkflowStep, WorkflowStep.table,
                properties=dict(
                    tags=relation(WorkflowStepTagAssociation, order_by=WorkflowStepTagAssociation.table.c.id, backref="workflow_steps"), 
                    annotations=relation( WorkflowStepAnnotationAssociation, order_by=WorkflowStepAnnotationAssociation.table.c.id, backref="workflow_steps" ) )
                )

assign_mapper( context, WorkflowOutput, WorkflowOutput.table,
    properties=dict(workflow_step = relation( WorkflowStep, backref='workflow_outputs', primaryjoin=(WorkflowStep.table.c.id == WorkflowOutput.table.c.workflow_step_id))))

assign_mapper( context, WorkflowStepConnection, WorkflowStepConnection.table,
    properties=dict( input_step=relation( WorkflowStep, backref="input_connections", cascade="all",
                                          primaryjoin=( WorkflowStepConnection.table.c.input_step_id == WorkflowStep.table.c.id ) ),
                     output_step=relation( WorkflowStep, backref="output_connections", cascade="all",
                                           primaryjoin=( WorkflowStepConnection.table.c.output_step_id == WorkflowStep.table.c.id ) ) ) )


assign_mapper( context, StoredWorkflow, StoredWorkflow.table,
    properties=dict( user=relation( User,
                                    primaryjoin=( User.table.c.id == StoredWorkflow.table.c.user_id ),
                                    backref='stored_workflows' ),
                     workflows=relation( Workflow, backref='stored_workflow',
                                         cascade="all, delete-orphan",
                                         primaryjoin=( StoredWorkflow.table.c.id == Workflow.table.c.stored_workflow_id ) ),
                     latest_workflow=relation( Workflow, post_update=True,
                                               primaryjoin=( StoredWorkflow.table.c.latest_workflow_id == Workflow.table.c.id ),
                                               lazy=False ),
                     tags=relation( StoredWorkflowTagAssociation, order_by=StoredWorkflowTagAssociation.table.c.id, backref="stored_workflows" ),
                     owner_tags=relation( StoredWorkflowTagAssociation,
                                    primaryjoin=and_( StoredWorkflow.table.c.id == StoredWorkflowTagAssociation.table.c.stored_workflow_id,
                                                      StoredWorkflow.table.c.user_id == StoredWorkflowTagAssociation.table.c.user_id ),
                                    order_by=StoredWorkflowTagAssociation.table.c.id ),
                     annotations=relation( StoredWorkflowAnnotationAssociation, order_by=StoredWorkflowAnnotationAssociation.table.c.id, backref="stored_workflows" ),
                     ratings=relation( StoredWorkflowRatingAssociation, order_by=StoredWorkflowRatingAssociation.table.c.id, backref="stored_workflows" ) )
                   )

# Set up proxy so that 
#   StoredWorkflow.users_shared_with
# returns a list of users that workflow is shared with.
StoredWorkflow.users_shared_with_dot_users = association_proxy( 'users_shared_with', 'user' )

assign_mapper( context, StoredWorkflowUserShareAssociation, StoredWorkflowUserShareAssociation.table,
    properties=dict( user=relation( User, backref='workflows_shared_by_others' ),
                     stored_workflow=relation( StoredWorkflow, backref='users_shared_with' )
                   ) )

assign_mapper( context, StoredWorkflowMenuEntry, StoredWorkflowMenuEntry.table,
    properties=dict( stored_workflow=relation( StoredWorkflow ) ) )

assign_mapper( context, WorkflowInvocation, WorkflowInvocation.table,
    properties=dict(
        steps=relation( WorkflowInvocationStep, backref='workflow_invocation', lazy=False ),
        workflow=relation( Workflow ) ) )

assign_mapper( context, WorkflowInvocationStep, WorkflowInvocationStep.table,
    properties=dict(
        workflow_step = relation( WorkflowStep ),
        job = relation( Job, backref=backref( 'workflow_invocation_step', uselist=False ) ) ) )

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
                     tags=relation(PageTagAssociation, order_by=PageTagAssociation.table.c.id, backref="pages"),
                     annotations=relation( PageAnnotationAssociation, order_by=PageAnnotationAssociation.table.c.id, backref="pages" ),
                     ratings=relation( PageRatingAssociation, order_by=PageRatingAssociation.table.c.id, backref="pages" )  
                   ) )
                   
assign_mapper( context, ToolShedRepository, ToolShedRepository.table,
    properties=dict( tool_versions=relation( ToolVersion,
                                             primaryjoin=( ToolShedRepository.table.c.id == ToolVersion.table.c.tool_shed_repository_id ),
                                             backref='tool_shed_repository' ) ) )

assign_mapper( context, ToolVersion, ToolVersion.table )

assign_mapper( context, ToolVersionAssociation, ToolVersionAssociation.table )

# Set up proxy so that 
#   Page.users_shared_with
# returns a list of users that page is shared with.
Page.users_shared_with_dot_users = association_proxy( 'users_shared_with', 'user' )
                   
assign_mapper( context, PageUserShareAssociation, PageUserShareAssociation.table,
   properties=dict( user=relation( User, backref='pages_shared_by_others' ),
                    page=relation( Page, backref='users_shared_with' )
                  ) )

assign_mapper( context, VisualizationRevision, VisualizationRevision.table )

assign_mapper( context, Visualization, Visualization.table,
    properties=dict( user=relation( User ),
                     revisions=relation( VisualizationRevision, backref='visualization',
                                         cascade="all, delete-orphan",
                                         primaryjoin=( Visualization.table.c.id == VisualizationRevision.table.c.visualization_id ) ),
                     latest_revision=relation( VisualizationRevision, post_update=True,
                                               primaryjoin=( Visualization.table.c.latest_revision_id == VisualizationRevision.table.c.id ),
                                               lazy=False ),
                     tags=relation( VisualizationTagAssociation, order_by=VisualizationTagAssociation.table.c.id, backref="visualizations" ),
                     annotations=relation( VisualizationAnnotationAssociation, order_by=VisualizationAnnotationAssociation.table.c.id, backref="visualizations" ),
                     ratings=relation( VisualizationRatingAssociation, order_by=VisualizationRatingAssociation.table.c.id, backref="visualizations" ) 
                   ) )
                   
# Set up proxy so that 
#   Visualization.users_shared_with
# returns a list of users that visualization is shared with.
Visualization.users_shared_with_dot_users = association_proxy( 'users_shared_with', 'user' )
                   
assign_mapper( context, VisualizationUserShareAssociation, VisualizationUserShareAssociation.table,
  properties=dict( user=relation( User, backref='visualizations_shared_by_others' ),
                   visualization=relation( Visualization, backref='users_shared_with' )
                 ) )
                 
# Tag tables.

assign_mapper( context, Tag, Tag.table,
    properties=dict( children=relation(Tag, backref=backref( 'parent', remote_side=[Tag.table.c.id] ) )  
                     ) )

assign_mapper( context, HistoryTagAssociation, HistoryTagAssociation.table,
    properties=dict( tag=relation(Tag, backref="tagged_histories"), user=relation( User ) )
                     )

assign_mapper( context, DatasetTagAssociation, DatasetTagAssociation.table,
    properties=dict( tag=relation(Tag, backref="tagged_datasets"), user=relation( User ) )
                     )

assign_mapper( context, HistoryDatasetAssociationTagAssociation, HistoryDatasetAssociationTagAssociation.table,
    properties=dict( tag=relation(Tag, backref="tagged_history_dataset_associations"), user=relation( User ) )
                     )

assign_mapper( context, PageTagAssociation, PageTagAssociation.table,
    properties=dict( tag=relation(Tag, backref="tagged_pages"), user=relation( User ) )
                    )
                    
assign_mapper( context, StoredWorkflowTagAssociation, StoredWorkflowTagAssociation.table,
    properties=dict( tag=relation(Tag, backref="tagged_workflows"), user=relation( User ) )
                    )
                    
assign_mapper( context, WorkflowStepTagAssociation, WorkflowStepTagAssociation.table,
    properties=dict( tag=relation(Tag, backref="tagged_workflow_steps"), user=relation( User ) )
                    )
                    
assign_mapper( context, VisualizationTagAssociation, VisualizationTagAssociation.table,
    properties=dict( tag=relation(Tag, backref="tagged_visualizations"), user=relation( User ) )
                    )
                    
assign_mapper( context, ToolTagAssociation, ToolTagAssociation.table,
    properties=dict( tag=relation(Tag, backref="tagged_tools"), user=relation( User ) )
                    )
                    
# Annotation tables.
                    
assign_mapper( context, HistoryAnnotationAssociation, HistoryAnnotationAssociation.table,
    properties=dict( history=relation( History ), user=relation( User ) )
                    )
                    
assign_mapper( context, HistoryDatasetAssociationAnnotationAssociation, HistoryDatasetAssociationAnnotationAssociation.table,
    properties=dict( hda=relation( HistoryDatasetAssociation ), user=relation( User ) )
                    )
                    
assign_mapper( context, StoredWorkflowAnnotationAssociation, StoredWorkflowAnnotationAssociation.table,
    properties=dict( stored_workflow=relation( StoredWorkflow ), user=relation( User ) )
                    )

assign_mapper( context, WorkflowStepAnnotationAssociation, WorkflowStepAnnotationAssociation.table,
    properties=dict( workflow_step=relation( WorkflowStep ), user=relation( User ) )
                    )
                    
assign_mapper( context, PageAnnotationAssociation, PageAnnotationAssociation.table,
    properties=dict( page=relation( Page ), user=relation( User ) )
                    )
                    
assign_mapper( context, VisualizationAnnotationAssociation, VisualizationAnnotationAssociation.table,
    properties=dict( visualization=relation( Visualization ), user=relation( User ) )
                    )
                    
# Rating tables.

assign_mapper( context, HistoryRatingAssociation, HistoryRatingAssociation.table,
    properties=dict( history=relation( History ), user=relation( User ) )
                    )
                    
assign_mapper( context, HistoryDatasetAssociationRatingAssociation, HistoryDatasetAssociationRatingAssociation.table,
    properties=dict( hda=relation( HistoryDatasetAssociation ), user=relation( User ) )
                    )
                    
assign_mapper( context, StoredWorkflowRatingAssociation, StoredWorkflowRatingAssociation.table,
    properties=dict( stored_workflow=relation( StoredWorkflow ), user=relation( User ) )
                    )

assign_mapper( context, PageRatingAssociation, PageRatingAssociation.table,
    properties=dict( page=relation( Page ), user=relation( User ) )
                    )

assign_mapper( context, VisualizationRatingAssociation, VisualizationRatingAssociation.table,
    properties=dict( visualization=relation( Visualization ), user=relation( User ) )
                    )

# User tables.
                    
assign_mapper( context, UserPreference, UserPreference.table, 
    properties = {}
              )
              
assign_mapper( context, UserAction, UserAction.table, 
  properties = dict( user=relation( User.mapper ) )
            )

assign_mapper( context, APIKeys, APIKeys.table, 
    properties = {} )
    
# Helper methods.

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

def init( file_path, url, engine_options={}, create_tables=False, database_query_profiling_proxy=False, object_store=None ):
    """Connect mappings to the database"""
    # Connect dataset to the file path
    Dataset.file_path = file_path
    # Connect dataset to object store
    Dataset.object_store = object_store
    # Load the appropriate db module
    load_egg_for_url( url )
    # Should we use the logging proxy?
    if database_query_profiling_proxy:
        import galaxy.model.orm.logging_connection_proxy as logging_connection_proxy
        proxy = logging_connection_proxy.LoggingProxy()
    else:
        proxy = None
    # Create the database engine
    engine = create_engine( url, proxy=proxy, **engine_options )
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
    # model.flush() has been removed.
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

