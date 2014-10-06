"""
Details of how the data model objects are mapped onto the relational database
are encapsulated here.
"""

import logging
import pkg_resources

from sqlalchemy import and_, asc, Boolean, Column, DateTime, desc, ForeignKey, Integer, MetaData, not_, Numeric, select, String, Table, TEXT, Unicode, UniqueConstraint
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.types import BigInteger
from sqlalchemy.orm import backref, object_session, relation, mapper, class_mapper
from sqlalchemy.orm.collections import attribute_mapped_collection

from galaxy import model
from galaxy.model.orm.engine_factory import build_engine
from galaxy.model.orm.now import now
from galaxy.model.custom_types import JSONType, MetadataType, TrimmedString, UUIDType
from galaxy.model.base import ModelMapping
from galaxy.security import GalaxyRBACAgent

log = logging.getLogger( __name__ )

metadata = MetaData()


model.User.table = Table( "galaxy_user", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "email", TrimmedString( 255 ), index=True, nullable=False ),
    Column( "username", TrimmedString( 255 ), index=True, unique=True ),
    Column( "password", TrimmedString( 255 ), nullable=False ),
    Column( "external", Boolean, default=False ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ),
    Column( "disk_usage", Numeric( 15, 0 ), index=True ) ,
    Column( "active", Boolean, index=True, default=True, nullable=False ),
    Column( "activation_token", TrimmedString( 64 ), nullable=True, index=True ) )


model.UserAddress.table = Table( "user_address", metadata,
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

model.UserOpenID.table = Table( "galaxy_user_openid", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "openid", TEXT, index=True, unique=True ),
    Column( "provider", TrimmedString( 255 ) ),
    )

model.History.table = Table( "history", metadata,
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

model.HistoryUserShareAssociation.table = Table( "history_user_share_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True )
    )

model.HistoryDatasetAssociation.table = Table( "history_dataset_association", metadata,
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
    Column( "visible", Boolean ),
    Column( "hidden_beneath_collection_instance_id", ForeignKey( "history_dataset_collection_association.id" ), nullable=True ),
    Column( "extended_metadata_id", Integer,
        ForeignKey( "extended_metadata.id" ), index=True )
    )

model.Dataset.table = Table( "dataset", metadata,
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
    Column( 'total_size', Numeric( 15, 0 ) ),
    Column( 'uuid', UUIDType() ) )

model.HistoryDatasetAssociationDisplayAtAuthorization.table = Table( "history_dataset_association_display_at_authorization", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "site", TrimmedString( 255 ) ) )

model.HistoryDatasetAssociationSubset.table = Table( "history_dataset_association_subset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "history_dataset_association_subset_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "location", Unicode(255), index=True) )

model.ImplicitlyConvertedDatasetAssociation.table = Table( "implicitly_converted_dataset_association", metadata,
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

model.ValidationError.table = Table( "validation_error", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "dataset_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "message", TrimmedString( 255 ) ),
    Column( "err_type", TrimmedString( 64 ) ),
    Column( "attributes", TEXT ) )

model.Group.table = Table( "galaxy_group", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", String( 255 ), index=True, unique=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

model.UserGroupAssociation.table = Table( "user_group_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "group_id", Integer, ForeignKey( "galaxy_group.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

model.UserRoleAssociation.table = Table( "user_role_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

model.GroupRoleAssociation.table = Table( "group_role_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "group_id", Integer, ForeignKey( "galaxy_group.id" ), index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

model.Role.table = Table( "role", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", String( 255 ), index=True, unique=True ),
    Column( "description", TEXT ),
    Column( "type", String( 40 ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

model.UserQuotaAssociation.table = Table( "user_quota_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "quota_id", Integer, ForeignKey( "quota.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

model.GroupQuotaAssociation.table = Table( "group_quota_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "group_id", Integer, ForeignKey( "galaxy_group.id" ), index=True ),
    Column( "quota_id", Integer, ForeignKey( "quota.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

model.Quota.table = Table( "quota", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", String( 255 ), index=True, unique=True ),
    Column( "description", TEXT ),
    Column( "bytes", BigInteger ),
    Column( "operation", String( 8 ) ),
    Column( "deleted", Boolean, index=True, default=False ) )

model.DefaultQuotaAssociation.table = Table( "default_quota_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "type", String( 32 ), index=True, unique=True ),
    Column( "quota_id", Integer, ForeignKey( "quota.id" ), index=True ) )

model.DatasetPermissions.table = Table( "dataset_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

model.LibraryPermissions.table = Table( "library_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "library_id", Integer, ForeignKey( "library.id" ), nullable=True, index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

model.LibraryFolderPermissions.table = Table( "library_folder_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "library_folder_id", Integer, ForeignKey( "library_folder.id" ), nullable=True, index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

model.LibraryDatasetPermissions.table = Table( "library_dataset_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "library_dataset_id", Integer, ForeignKey( "library_dataset.id" ), nullable=True, index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

model.LibraryDatasetDatasetAssociationPermissions.table = Table( "library_dataset_dataset_association_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), nullable=True, index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

model.DefaultUserPermissions.table = Table( "default_user_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "action", TEXT ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

model.DefaultHistoryPermissions.table = Table( "default_history_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "action", TEXT ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

model.LibraryDataset.table = Table( "library_dataset", metadata,
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

model.LibraryDatasetDatasetAssociation.table = Table( "library_dataset_dataset_association", metadata,
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
    Column( "message", TrimmedString( 255 ) ),
    Column( "extended_metadata_id", Integer,
        ForeignKey( "extended_metadata.id" ), index=True )
    )


model.ExtendedMetadata.table = Table("extended_metadata", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "data", JSONType ) )

model.ExtendedMetadataIndex.table = Table("extended_metadata_index", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "extended_metadata_id", Integer, ForeignKey("extended_metadata.id",
                                                        onupdate="CASCADE",
                                                        ondelete="CASCADE" ),
                                             index=True ),
    Column( "path", String( 255 )),
    Column( "value", TEXT))

model.Library.table = Table( "library", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "root_folder_id", Integer, ForeignKey( "library_folder.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", String( 255 ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ),
    Column( "description", TEXT ),
    Column( "synopsis", TEXT ) )

model.LibraryFolder.table = Table( "library_folder", metadata,
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

model.LibraryInfoAssociation.table = Table( 'library_info_association', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "library_id", Integer, ForeignKey( "library.id" ), index=True ),
    Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
    Column( "inheritable", Boolean, index=True, default=False ),
    Column( "deleted", Boolean, index=True, default=False ) )

model.LibraryFolderInfoAssociation.table = Table( 'library_folder_info_association', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "library_folder_id", Integer, ForeignKey( "library_folder.id" ), nullable=True, index=True ),
    Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
    Column( "inheritable", Boolean, index=True, default=False ),
    Column( "deleted", Boolean, index=True, default=False ) )

model.LibraryDatasetDatasetInfoAssociation.table = Table( 'library_dataset_dataset_info_association', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), nullable=True, index=True ),
    Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

model.Job.table = Table( "job", metadata,
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
    Column( "exit_code", Integer, nullable=True ),
    Column( "traceback", TEXT ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), index=True, nullable=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=True ),
    Column( "job_runner_name", String( 255 ) ),
    Column( "job_runner_external_id", String( 255 ) ),
    Column( "destination_id", String( 255 ), nullable=True ),
    Column( "destination_params", JSONType, nullable=True ),
    Column( "object_store_id", TrimmedString( 255 ), index=True ),
    Column( "imported", Boolean, default=False, index=True ),
    Column( "params", TrimmedString(255), index=True ),
    Column( "handler", TrimmedString( 255 ), index=True ) )

model.JobParameter.table = Table( "job_parameter", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "name", String(255) ),
    Column( "value", TEXT ) )

model.JobToInputDatasetAssociation.table = Table( "job_to_input_dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "name", String(255) ) )

model.JobToOutputDatasetAssociation.table = Table( "job_to_output_dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "name", String(255) ) )

model.JobToInputDatasetCollectionAssociation.table = Table( "job_to_input_dataset_collection", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "dataset_collection_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), index=True ),
    Column( "name", Unicode(255) ) )

model.JobToOutputDatasetCollectionAssociation.table = Table( "job_to_output_dataset_collection", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "dataset_collection_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), index=True ),
    Column( "name", Unicode(255) ) )

model.JobToInputLibraryDatasetAssociation.table = Table( "job_to_input_library_dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "ldda_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), index=True ),
    Column( "name", String(255) ) )

model.JobToOutputLibraryDatasetAssociation.table = Table( "job_to_output_library_dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "ldda_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), index=True ),
    Column( "name", String(255) ) )

model.ImplicitlyCreatedDatasetCollectionInput.table = Table( "implicitly_created_dataset_collection_inputs", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "dataset_collection_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), index=True ),
    Column( "input_dataset_collection_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), index=True ),
    Column( "name", Unicode(255) ) )

model.JobExternalOutputMetadata.table = Table( "job_external_output_metadata", metadata,
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

model.JobExportHistoryArchive.table = Table( "job_export_history_archive", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "compressed", Boolean, index=True, default=False ),
    Column( "history_attrs_filename", TEXT ),
    Column( "datasets_attrs_filename", TEXT ),
    Column( "jobs_attrs_filename", TEXT )
    )

model.JobImportHistoryArchive.table = Table( "job_import_history_archive", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "archive_dir", TEXT )
    )


JOB_METRIC_MAX_LENGTH = 1023

model.JobMetricText.table = Table(
    "job_metric_text",
    metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "plugin", Unicode(255), ),
    Column( "metric_name", Unicode(255), ),
    Column( "metric_value", Unicode(JOB_METRIC_MAX_LENGTH), ),
)

model.TaskMetricText.table = Table(
    "task_metric_text",
    metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "task_id", Integer, ForeignKey( "task.id" ), index=True ),
    Column( "plugin", Unicode(255), ),
    Column( "metric_name", Unicode(255), ),
    Column( "metric_value", Unicode(JOB_METRIC_MAX_LENGTH), ),
)


model.JobMetricNumeric.table = Table(
    "job_metric_numeric",
    metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "plugin", Unicode(255), ),
    Column( "metric_name", Unicode(255), ),
    Column( "metric_value", Numeric( 22, 7 ), ),
)


model.TaskMetricNumeric.table = Table(
    "task_metric_numeric",
    metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "task_id", Integer, ForeignKey( "task.id" ), index=True ),
    Column( "plugin", Unicode(255), ),
    Column( "metric_name", Unicode(255), ),
    Column( "metric_value", Numeric( 22, 7 ), ),
)


model.GenomeIndexToolData.table = Table( "genome_index_tool_data", metadata,
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

model.Task.table = Table( "task", metadata,
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
    Column( "exit_code", Integer, nullable=True ),
    Column( "info", TrimmedString ( 255 ) ),
    Column( "traceback", TEXT ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True, nullable=False ),
    Column( "working_directory", String(1024)),
    Column( "task_runner_name", String( 255 ) ),
    Column( "task_runner_external_id", String( 255 ) ),
    Column( "prepare_input_files_cmd", TEXT ) )

model.PostJobAction.table = Table("post_job_action", metadata,
    Column("id", Integer, primary_key=True),
    Column("workflow_step_id", Integer, ForeignKey( "workflow_step.id" ), index=True, nullable=False),
    Column("action_type", String(255), nullable=False),
    Column("output_name", String(255), nullable=True),
    Column("action_arguments", JSONType, nullable=True))

model.PostJobActionAssociation.table = Table("post_job_action_association", metadata,
    Column("id", Integer, primary_key=True),
    Column("job_id", Integer, ForeignKey( "job.id" ), index=True, nullable=False),
    Column("post_job_action_id", Integer, ForeignKey( "post_job_action.id" ), index=True, nullable=False))

model.DeferredJob.table = Table( "deferred_job", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "state", String( 64 ), index=True ),
    Column( "plugin", String( 128 ), index=True ),
    Column( "params", JSONType ) )

model.TransferJob.table = Table( "transfer_job", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "state", String( 64 ), index=True ),
    Column( "path", String( 1024 ) ),
    Column( "info", TEXT ),
    Column( "pid", Integer ),
    Column( "socket", Integer ),
    Column( "params", JSONType ) )

model.DatasetCollection.table = Table( "dataset_collection", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "collection_type", Unicode(255), nullable=False ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
)

model.HistoryDatasetCollectionAssociation.table = Table( "history_dataset_collection_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "collection_id", Integer, ForeignKey( "dataset_collection.id" ), index=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "name", TrimmedString( 255 ) ),
    Column( "hid", Integer ),
    Column( "visible", Boolean ),
    Column( "deleted", Boolean, default=False ),
    Column( "copied_from_history_dataset_collection_association_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), nullable=True ),
    Column( "implicit_output_name", Unicode(255), nullable=True ),
)

model.LibraryDatasetCollectionAssociation.table = Table( "library_dataset_collection_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "collection_id", Integer, ForeignKey( "dataset_collection.id" ), index=True ),
    Column( "folder_id", Integer, ForeignKey( "library_folder.id" ), index=True ),
    Column( "name", TrimmedString( 255 ) ),
    Column( "deleted", Boolean, default=False ),
)

model.DatasetCollectionElement.table = Table( "dataset_collection_element", metadata,
    Column( "id", Integer, primary_key=True ),
    # Parent collection id describing what collection this element belongs to.
    Column( "dataset_collection_id", Integer, ForeignKey( "dataset_collection.id" ), index=True, nullable=False ),
    # Child defined by this association - HDA, LDDA, or another dataset association...
    Column( "hda_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True, nullable=True ),
    Column( "ldda_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), index=True, nullable=True ),
    Column( "child_collection_id", Integer, ForeignKey( "dataset_collection.id" ), index=True, nullable=True ),
    # Element index and identifier to define this parent-child relationship.
    Column( "element_index", Integer ),
    Column( "element_identifier", Unicode(255), ),
)

model.Event.table = Table( "event", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True, nullable=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=True ),
    Column( "message", TrimmedString( 1024 ) ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), index=True, nullable=True ),
    Column( "tool_id", String( 255 ) ) )

model.GalaxySession.table = Table( "galaxy_session", metadata,
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

model.GalaxySessionToHistoryAssociation.table = Table( "galaxy_session_to_history", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), index=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ) )

model.StoredWorkflow.table = Table( "stored_workflow", metadata,
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

model.Workflow.table = Table( "workflow", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True, nullable=False ),
    Column( "name", TEXT ),
    Column( "has_cycles", Boolean ),
    Column( "has_errors", Boolean ),
    Column( "uuid", UUIDType, nullable=True )
    )

model.WorkflowStep.table = Table( "workflow_step", metadata,
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

model.WorkflowStepConnection.table = Table( "workflow_step_connection", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "output_step_id", Integer, ForeignKey( "workflow_step.id" ), index=True ),
    Column( "input_step_id", Integer, ForeignKey( "workflow_step.id" ), index=True ),
    Column( "output_name", TEXT ),
    Column( "input_name", TEXT)
    )

model.WorkflowOutput.table = Table( "workflow_output", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "workflow_step_id", Integer, ForeignKey("workflow_step.id"), index=True, nullable=False),
    Column( "output_name", String(255), nullable=True)
    )

model.WorkflowInvocation.table = Table( "workflow_invocation", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "workflow_id", Integer, ForeignKey( "workflow.id" ), index=True, nullable=False )
    )

model.WorkflowInvocationStep.table = Table( "workflow_invocation_step", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "workflow_invocation_id", Integer, ForeignKey( "workflow_invocation.id" ), index=True, nullable=False ),
    Column( "workflow_step_id",  Integer, ForeignKey( "workflow_step.id" ), index=True, nullable=False ),
    Column( "job_id",  Integer, ForeignKey( "job.id" ), index=True, nullable=True )
    )

model.StoredWorkflowUserShareAssociation.table = Table( "stored_workflow_user_share_connection", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True )
    )

model.StoredWorkflowMenuEntry.table = Table( "stored_workflow_menu_entry", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "order_index", Integer ) )

model.MetadataFile.table = Table( "metadata_file", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "name", TEXT ),
    Column( "hda_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True, nullable=True ),
    Column( "lda_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), index=True, nullable=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "object_store_id", TrimmedString( 255 ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ) )

model.FormDefinitionCurrent.table = Table('form_definition_current', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "latest_form_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ))

model.FormDefinition.table = Table('form_definition', metadata,
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

model.ExternalService.table = Table( 'external_service', metadata,
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

model.RequestType.table = Table('request_type', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), nullable=False ),
    Column( "desc", TEXT ),
    Column( "request_form_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "sample_form_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

model.RequestTypeExternalServiceAssociation.table = Table( "request_type_external_service_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "request_type_id", Integer, ForeignKey( "request_type.id" ), index=True ),
    Column( "external_service_id", Integer, ForeignKey( "external_service.id" ), index=True ) )

model.RequestTypePermissions.table = Table( "request_type_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "request_type_id", Integer, ForeignKey( "request_type.id" ), nullable=True, index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

model.FormValues.table = Table('form_values', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "content", JSONType()) )

model.Request.table = Table('request', metadata,
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

model.RequestEvent.table = Table('request_event', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "request_id", Integer, ForeignKey( "request.id" ), index=True ),
    Column( "state", TrimmedString( 255 ),  index=True ),
    Column( "comment", TEXT ) )

model.Sample.table = Table('sample', metadata,
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

model.SampleState.table = Table('sample_state', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), nullable=False ),
    Column( "desc", TEXT ),
    Column( "request_type_id", Integer, ForeignKey( "request_type.id" ), index=True ) )

model.SampleEvent.table = Table('sample_event', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "sample_id", Integer, ForeignKey( "sample.id" ), index=True ),
    Column( "sample_state_id", Integer, ForeignKey( "sample_state.id" ), index=True ),
    Column( "comment", TEXT ) )

model.SampleDataset.table = Table('sample_dataset', metadata,
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

model.Run.table = Table( 'run', metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "subindex", TrimmedString( 255 ), index=True ) )

model.RequestTypeRunAssociation.table = Table( "request_type_run_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "request_type_id", Integer, ForeignKey( "request_type.id" ), index=True, nullable=False ),
    Column( "run_id", Integer, ForeignKey( "run.id" ), index=True, nullable=False ) )

model.SampleRunAssociation.table = Table( "sample_run_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "sample_id", Integer, ForeignKey( "sample.id" ), index=True, nullable=False ),
    Column( "run_id", Integer, ForeignKey( "run.id" ), index=True, nullable=False ) )

model.Page.table = Table( "page", metadata,
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

model.PageRevision.table = Table( "page_revision", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True, nullable=False ),
    Column( "title", TEXT ),
    Column( "content", TEXT )
    )

model.PageUserShareAssociation.table = Table( "page_user_share_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True )
    )

model.Visualization.table = Table( "visualization", metadata,
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

model.VisualizationRevision.table = Table( "visualization_revision", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "visualization_id", Integer, ForeignKey( "visualization.id" ), index=True, nullable=False ),
    Column( "title", TEXT ),
    Column( "dbkey", TEXT, index=True ),
    Column( "config", JSONType )
    )

model.VisualizationUserShareAssociation.table = Table( "visualization_user_share_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "visualization_id", Integer, ForeignKey( "visualization.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True )
    )

#Data Manager tables
model.DataManagerHistoryAssociation.table = Table( "data_manager_history_association", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True )
    )

model.DataManagerJobAssociation.table = Table( "data_manager_job_association", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "data_manager_id", TEXT, index=True )
    )

# Tagging tables.

model.Tag.table = Table( "tag", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "type", Integer ),
    Column( "parent_id", Integer, ForeignKey( "tag.id" ) ),
    Column( "name", TrimmedString(255) ),
    UniqueConstraint( "name" ) )

model.HistoryTagAssociation.table = Table( "history_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

model.DatasetTagAssociation.table = Table( "dataset_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

model.HistoryDatasetAssociationTagAssociation.table = Table( "history_dataset_association_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

model.StoredWorkflowTagAssociation.table = Table( "stored_workflow_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", Unicode(255), index=True),
    Column( "value", Unicode(255), index=True),
    Column( "user_value", Unicode(255), index=True) )

model.PageTagAssociation.table = Table( "page_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

model.WorkflowStepTagAssociation.table = Table( "workflow_step_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "workflow_step_id", Integer, ForeignKey( "workflow_step.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", Unicode(255), index=True),
    Column( "value", Unicode(255), index=True),
    Column( "user_value", Unicode(255), index=True) )

model.VisualizationTagAssociation.table = Table( "visualization_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "visualization_id", Integer, ForeignKey( "visualization.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

model.HistoryDatasetCollectionTagAssociation.table = Table( "history_dataset_collection_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_collection_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

model.LibraryDatasetCollectionTagAssociation.table = Table( "library_dataset_collection_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "library_dataset_collection_id", Integer, ForeignKey( "library_dataset_collection_association.id" ), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

model.ToolTagAssociation.table = Table( "tool_tag_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "tool_id", TrimmedString(255), index=True ),
    Column( "tag_id", Integer, ForeignKey( "tag.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "user_tname", TrimmedString(255), index=True),
    Column( "value", TrimmedString(255), index=True),
    Column( "user_value", TrimmedString(255), index=True) )

# Annotation tables.

model.HistoryAnnotationAssociation.table = Table( "history_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT, index=True) )

model.HistoryDatasetAssociationAnnotationAssociation.table = Table( "history_dataset_association_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT, index=True) )

model.StoredWorkflowAnnotationAssociation.table = Table( "stored_workflow_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT, index=True) )

model.WorkflowStepAnnotationAssociation.table = Table( "workflow_step_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "workflow_step_id", Integer, ForeignKey( "workflow_step.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT, index=True) )

model.PageAnnotationAssociation.table = Table( "page_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT, index=True) )

model.VisualizationAnnotationAssociation.table = Table( "visualization_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "visualization_id", Integer, ForeignKey( "visualization.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT, index=True) )

model.HistoryDatasetCollectionAnnotationAssociation.table = Table( "history_dataset_collection_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_collection_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT, index=True) )

model.LibraryDatasetCollectionAnnotationAssociation.table = Table( "library_dataset_collection_annotation_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "library_dataset_collection_id", Integer, ForeignKey( "library_dataset_collection_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "annotation", TEXT, index=True) )

# Ratings tables.
model.HistoryRatingAssociation.table = Table( "history_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True) )

model.HistoryDatasetAssociationRatingAssociation.table = Table( "history_dataset_association_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True) )

model.StoredWorkflowRatingAssociation.table = Table( "stored_workflow_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True) )

model.PageRatingAssociation.table = Table( "page_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "page_id", Integer, ForeignKey( "page.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True) )

model.VisualizationRatingAssociation.table = Table( "visualization_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "visualization_id", Integer, ForeignKey( "visualization.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True) )

model.HistoryDatasetCollectionRatingAssociation.table = Table( "history_dataset_collection_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_dataset_collection_id", Integer, ForeignKey( "history_dataset_collection_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True) )

model.LibraryDatasetCollectionRatingAssociation.table = Table( "library_dataset_collection_rating_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "library_dataset_collection_id", Integer, ForeignKey( "library_dataset_collection_association.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "rating", Integer, index=True) )

# User tables.

model.UserPreference.table = Table( "user_preference", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "name", Unicode( 255 ), index=True),
    Column( "value", Unicode( 1024 ) ) )

model.UserAction.table = Table( "user_action", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), index=True ),
    Column( "action", Unicode( 255 ) ),
    Column( "context", Unicode( 512 ) ),
    Column( "params", Unicode( 1024 ) ) )

model.APIKeys.table = Table( "api_keys", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "key", TrimmedString( 32 ), index=True, unique=True ) )


# With the tables defined we can define the mappers and setup the
# relationships between the model objects.
def simple_mapping( model, **kwds ):
    mapper( model, model.table, properties=kwds )


mapper( model.Sample, model.Sample.table,
               properties=dict(
                    events=relation( model.SampleEvent, backref="sample",
                        order_by=desc( model.SampleEvent.table.c.update_time ) ),
                    datasets=relation( model.SampleDataset, backref="sample",
                        order_by=desc( model.SampleDataset.table.c.update_time ) ),
                    values=relation( model.FormValues,
                        primaryjoin=( model.Sample.table.c.form_values_id == model.FormValues.table.c.id ) ),
                    request=relation( model.Request,
                        primaryjoin=( model.Sample.table.c.request_id == model.Request.table.c.id ) ),
                    folder=relation( model.LibraryFolder,
                        primaryjoin=( model.Sample.table.c.folder_id == model.LibraryFolder.table.c.id ) ),
                    library=relation( model.Library,
                        primaryjoin=( model.Sample.table.c.library_id == model.Library.table.c.id ) ),
                    history=relation( model.History,
                        primaryjoin=( model.Sample.table.c.history_id == model.History.table.c.id ) ),
            ) )


mapper( model.FormValues, model.FormValues.table,
               properties=dict( form_definition=relation( model.FormDefinition,
                                                          primaryjoin=( model.FormValues.table.c.form_definition_id ==
                                                              model.FormDefinition.table.c.id ) )
             )
)

mapper( model.Request, model.Request.table,
               properties=dict( values=relation( model.FormValues,
                                                 primaryjoin=( model.Request.table.c.form_values_id == model.FormValues.table.c.id ) ),
                                type=relation( model.RequestType,
                                               primaryjoin=( model.Request.table.c.request_type_id == model.RequestType.table.c.id ) ),
                                user=relation( model.User,
                                               primaryjoin=( model.Request.table.c.user_id == model.User.table.c.id ),
                                               backref="requests" ),
                                samples=relation( model.Sample,
                                                  primaryjoin=( model.Request.table.c.id == model.Sample.table.c.request_id ),
                                                  order_by=asc( model.Sample.table.c.id ) ),
                                events=relation( model.RequestEvent, backref="request",
                                                 order_by=desc( model.RequestEvent.table.c.update_time ) )
                              ) )

mapper( model.RequestEvent, model.RequestEvent.table,
               properties=None )

mapper( model.ExternalService, model.ExternalService.table,
               properties=dict( form_definition=relation( model.FormDefinition,
                                                       primaryjoin=( model.ExternalService.table.c.form_definition_id ==
                                                           model.FormDefinition.table.c.id ) ),
                                form_values=relation( model.FormValues,
                                                      primaryjoin=( model.ExternalService.table.c.form_values_id ==
                                                          model.FormValues.table.c.id ) )
                                ) )

mapper( model.RequestType, model.RequestType.table,
               properties=dict( states=relation( model.SampleState,
                                                 backref="request_type",
                                                 primaryjoin=( model.RequestType.table.c.id == model.SampleState.table.c.request_type_id ),
                                                 order_by=asc( model.SampleState.table.c.update_time ) ),
                                request_form=relation( model.FormDefinition,
                                                       primaryjoin=( model.RequestType.table.c.request_form_id == model.FormDefinition.table.c.id ) ),
                                sample_form=relation( model.FormDefinition,
                                                      primaryjoin=( model.RequestType.table.c.sample_form_id == model.FormDefinition.table.c.id ) ),
                              ) )

mapper( model.RequestTypeExternalServiceAssociation, model.RequestTypeExternalServiceAssociation.table,
    properties=dict(
        request_type=relation( model.RequestType,
                               primaryjoin=( ( model.RequestTypeExternalServiceAssociation.table.c.request_type_id == model.RequestType.table.c.id ) ), backref="external_service_associations" ),
        external_service=relation( model.ExternalService,
                                   primaryjoin=( model.RequestTypeExternalServiceAssociation.table.c.external_service_id
                                       == model.ExternalService.table.c.id ) )
    )
)


mapper( model.RequestTypePermissions, model.RequestTypePermissions.table,
    properties=dict(
        request_type=relation( model.RequestType, backref="actions" ),
        role=relation( model.Role, backref="request_type_actions" )
    )
)

mapper( model.FormDefinition, model.FormDefinition.table,
               properties=dict( current=relation( model.FormDefinitionCurrent,
                                                  primaryjoin=( model.FormDefinition.table.c.form_definition_current_id == model.FormDefinitionCurrent.table.c.id ) )
                              ) )
mapper( model.FormDefinitionCurrent, model.FormDefinitionCurrent.table,
                properties=dict( forms=relation( model.FormDefinition, backref='form_definition_current',
                                                 cascade="all, delete-orphan",
                                                 primaryjoin=( model.FormDefinitionCurrent.table.c.id == model.FormDefinition.table.c.form_definition_current_id ) ),
                                 latest_form=relation( model.FormDefinition, post_update=True,
                                                       primaryjoin=( model.FormDefinitionCurrent.table.c.latest_form_id == model.FormDefinition.table.c.id ) )
                               ) )

mapper( model.SampleEvent, model.SampleEvent.table,
               properties=dict( state=relation( model.SampleState,
                                                primaryjoin=( model.SampleEvent.table.c.sample_state_id == model.SampleState.table.c.id ) ),

                                ) )

mapper( model.SampleState, model.SampleState.table,
               properties=None )

mapper( model.SampleDataset, model.SampleDataset.table,
               properties=dict( external_service=relation( model.ExternalService,
                                                           primaryjoin=( model.SampleDataset.table.c.external_service_id == model.ExternalService.table.c.id ) )
    )
)


mapper( model.SampleRunAssociation, model.SampleRunAssociation.table,
               properties=dict( sample=relation( model.Sample, backref="runs", order_by=desc( model.Run.table.c.update_time ) ),
                                run=relation( model.Run, backref="samples", order_by=asc( model.Sample.table.c.id ) ) ) )

mapper( model.RequestTypeRunAssociation, model.RequestTypeRunAssociation.table,
               properties=dict( request_type=relation( model.RequestType, backref="run" ),
                                run=relation( model.Run, backref="request_type" ) ) )

mapper( model.Run, model.Run.table,
                properties=dict( template=relation( model.FormDefinition,
                                                    primaryjoin=( model.Run.table.c.form_definition_id == model.FormDefinition.table.c.id ) ),
                                 info=relation( model.FormValues,
                                                primaryjoin=( model.Run.table.c.form_values_id == model.FormValues.table.c.id ) ) ) )

mapper( model.UserAddress, model.UserAddress.table,
               properties=dict(
                    user=relation( model.User,
                                   primaryjoin=( model.UserAddress.table.c.user_id == model.User.table.c.id ),
                                   backref='addresses',
                                   order_by=desc(model.UserAddress.table.c.update_time)),
                ) )

mapper( model.UserOpenID, model.UserOpenID.table,
    properties=dict(
        session=relation( model.GalaxySession,
                          primaryjoin=( model.UserOpenID.table.c.session_id == model.GalaxySession.table.c.id ),
                          backref='openids',
                          order_by=desc( model.UserOpenID.table.c.update_time ) ),
        user=relation( model.User,
                       primaryjoin=( model.UserOpenID.table.c.user_id == model.User.table.c.id ),
                       backref='openids',
                       order_by=desc( model.UserOpenID.table.c.update_time ) ) ) )


mapper( model.ValidationError, model.ValidationError.table )

simple_mapping( model.HistoryDatasetAssociation,
    dataset=relation(
        model.Dataset,
        primaryjoin=( model.Dataset.table.c.id == model.HistoryDatasetAssociation.table.c.dataset_id ), lazy=False ),
    # .history defined in History mapper
    copied_from_history_dataset_association=relation(
        model.HistoryDatasetAssociation,
        primaryjoin=( model.HistoryDatasetAssociation.table.c.copied_from_history_dataset_association_id == model.HistoryDatasetAssociation.table.c.id ),
        remote_side=[model.HistoryDatasetAssociation.table.c.id],
        uselist=False ),
    copied_to_history_dataset_associations=relation(
        model.HistoryDatasetAssociation,
        primaryjoin=( model.HistoryDatasetAssociation.table.c.copied_from_history_dataset_association_id == model.HistoryDatasetAssociation.table.c.id ) ),
    copied_from_library_dataset_dataset_association=relation(
        model.LibraryDatasetDatasetAssociation,
        primaryjoin=( model.HistoryDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id == model.LibraryDatasetDatasetAssociation.table.c.id ),
        uselist=False ),
    copied_to_library_dataset_dataset_associations=relation(
        model.LibraryDatasetDatasetAssociation,
        primaryjoin=( model.HistoryDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id == model.LibraryDatasetDatasetAssociation.table.c.id ) ),
    implicitly_converted_datasets=relation(
        model.ImplicitlyConvertedDatasetAssociation,
        primaryjoin=( model.ImplicitlyConvertedDatasetAssociation.table.c.hda_parent_id == model.HistoryDatasetAssociation.table.c.id ) ),
    implicitly_converted_parent_datasets=relation(
        model.ImplicitlyConvertedDatasetAssociation,
        primaryjoin=( model.ImplicitlyConvertedDatasetAssociation.table.c.hda_id == model.HistoryDatasetAssociation.table.c.id ) ),
    children=relation(
        model.HistoryDatasetAssociation,
        primaryjoin=( model.HistoryDatasetAssociation.table.c.parent_id == model.HistoryDatasetAssociation.table.c.id ),
        backref=backref( "parent", primaryjoin=( model.HistoryDatasetAssociation.table.c.parent_id == model.HistoryDatasetAssociation.table.c.id ), remote_side=[model.HistoryDatasetAssociation.table.c.id], uselist=False ) ),
    visible_children=relation(
        model.HistoryDatasetAssociation,
        primaryjoin=( ( model.HistoryDatasetAssociation.table.c.parent_id == model.HistoryDatasetAssociation.table.c.id ) & ( model.HistoryDatasetAssociation.table.c.visible == True ) ) ),
    tags=relation( model.HistoryDatasetAssociationTagAssociation, order_by=model.HistoryDatasetAssociationTagAssociation.table.c.id, backref='history_tag_associations' ),
    annotations=relation( model.HistoryDatasetAssociationAnnotationAssociation, order_by=model.HistoryDatasetAssociationAnnotationAssociation.table.c.id, backref="hdas" ),
    ratings=relation( model.HistoryDatasetAssociationRatingAssociation, order_by=model.HistoryDatasetAssociationRatingAssociation.table.c.id, backref="hdas" ),
    extended_metadata=relation(
            model.ExtendedMetadata,
            primaryjoin=( ( model.HistoryDatasetAssociation.table.c.extended_metadata_id == model.ExtendedMetadata.table.c.id ) )
        ),
    hidden_beneath_collection_instance=relation(
        model.HistoryDatasetCollectionAssociation,
        primaryjoin=( ( model.HistoryDatasetAssociation.table.c.hidden_beneath_collection_instance_id == model.HistoryDatasetCollectionAssociation.table.c.id ) ),
        uselist=False,
        backref="hidden_dataset_instances",
    )
)

simple_mapping( model.Dataset,
    history_associations=relation(
        model.HistoryDatasetAssociation,
        primaryjoin=( model.Dataset.table.c.id == model.HistoryDatasetAssociation.table.c.dataset_id ) ),
    active_history_associations=relation(
        model.HistoryDatasetAssociation,
        primaryjoin=( ( model.Dataset.table.c.id == model.HistoryDatasetAssociation.table.c.dataset_id ) & ( model.HistoryDatasetAssociation.table.c.deleted == False ) & ( model.HistoryDatasetAssociation.table.c.purged == False ) ) ),
    purged_history_associations=relation(
        model.HistoryDatasetAssociation,
        primaryjoin=( ( model.Dataset.table.c.id == model.HistoryDatasetAssociation.table.c.dataset_id ) & ( model.HistoryDatasetAssociation.table.c.purged == True ) ) ),
    library_associations=relation(
        model.LibraryDatasetDatasetAssociation,
        primaryjoin=( model.Dataset.table.c.id == model.LibraryDatasetDatasetAssociation.table.c.dataset_id ) ),
    active_library_associations=relation(
        model.LibraryDatasetDatasetAssociation,
        primaryjoin=( ( model.Dataset.table.c.id == model.LibraryDatasetDatasetAssociation.table.c.dataset_id ) & ( model.LibraryDatasetDatasetAssociation.table.c.deleted == False ) ) ),
    tags=relation(model.DatasetTagAssociation, order_by=model.DatasetTagAssociation.table.c.id, backref='datasets')
)

mapper( model.HistoryDatasetAssociationDisplayAtAuthorization, model.HistoryDatasetAssociationDisplayAtAuthorization.table,
    properties=dict( history_dataset_association = relation( model.HistoryDatasetAssociation ),
                     user = relation( model.User ) ) )

mapper( model.HistoryDatasetAssociationSubset, model.HistoryDatasetAssociationSubset.table,
    properties=dict( hda = relation( model.HistoryDatasetAssociation,
                        primaryjoin=( model.HistoryDatasetAssociationSubset.table.c.history_dataset_association_id == model.HistoryDatasetAssociation.table.c.id ) ),
                     subset = relation( model.HistoryDatasetAssociation,
                        primaryjoin=( model.HistoryDatasetAssociationSubset.table.c.history_dataset_association_subset_id == model.HistoryDatasetAssociation.table.c.id ) )
                    ) )

mapper( model.ImplicitlyConvertedDatasetAssociation, model.ImplicitlyConvertedDatasetAssociation.table,
    properties=dict( parent_hda=relation(
                        model.HistoryDatasetAssociation,
                        primaryjoin=( model.ImplicitlyConvertedDatasetAssociation.table.c.hda_parent_id == model.HistoryDatasetAssociation.table.c.id ) ),
                     parent_ldda=relation(
                        model.LibraryDatasetDatasetAssociation,
                        primaryjoin=( model.ImplicitlyConvertedDatasetAssociation.table.c.ldda_parent_id == model.LibraryDatasetDatasetAssociation.table.c.id ) ),
                     dataset_ldda=relation(
                        model.LibraryDatasetDatasetAssociation,
                        primaryjoin=( model.ImplicitlyConvertedDatasetAssociation.table.c.ldda_id == model.LibraryDatasetDatasetAssociation.table.c.id ) ),
                     dataset=relation(
                        model.HistoryDatasetAssociation,
                        primaryjoin=( model.ImplicitlyConvertedDatasetAssociation.table.c.hda_id == model.HistoryDatasetAssociation.table.c.id ) ) ) )

mapper( model.History, model.History.table,
    properties=dict( galaxy_sessions=relation( model.GalaxySessionToHistoryAssociation ),
                     datasets=relation( model.HistoryDatasetAssociation, backref="history", order_by=asc(model.HistoryDatasetAssociation.table.c.hid) ),
                     exports=relation( model.JobExportHistoryArchive, primaryjoin=( model.JobExportHistoryArchive.table.c.history_id == model.History.table.c.id ), order_by=desc( model.JobExportHistoryArchive.table.c.id ) ),
                     active_datasets=relation(
                        model.HistoryDatasetAssociation,
                        primaryjoin=(
                            ( model.HistoryDatasetAssociation.table.c.history_id == model.History.table.c.id ) & not_( model.HistoryDatasetAssociation.table.c.deleted )
                        ),
                        order_by=asc( model.HistoryDatasetAssociation.table.c.hid ),
                        viewonly=True
                     ),
                     active_dataset_collections=relation(
                        model.HistoryDatasetCollectionAssociation,
                        primaryjoin=(
                            ( model.HistoryDatasetCollectionAssociation.table.c.history_id ) == model.History.table.c.id ) & not_( model.HistoryDatasetCollectionAssociation.table.c.deleted ),
                        order_by=asc( model.HistoryDatasetCollectionAssociation.table.c.hid ),
                        viewonly=True,
                     ),
                     visible_datasets=relation(
                        model.HistoryDatasetAssociation,
                        primaryjoin=( ( model.HistoryDatasetAssociation.table.c.history_id == model.History.table.c.id ) & not_( model.HistoryDatasetAssociation.table.c.deleted ) & model.HistoryDatasetAssociation.table.c.visible ),
                        order_by=asc( model.HistoryDatasetAssociation.table.c.hid ),
                        viewonly=True,
                     ),
                     visible_dataset_collections=relation(
                        model.HistoryDatasetCollectionAssociation,
                        primaryjoin=( ( model.HistoryDatasetCollectionAssociation.table.c.history_id == model.History.table.c.id ) & not_( model.HistoryDatasetCollectionAssociation.table.c.deleted ) & model.HistoryDatasetCollectionAssociation.table.c.visible ),
                        order_by=asc( model.HistoryDatasetCollectionAssociation.table.c.hid ),
                        viewonly=True,
                     ),
                     tags=relation( model.HistoryTagAssociation, order_by=model.HistoryTagAssociation.table.c.id, backref="histories" ),
                     annotations=relation( model.HistoryAnnotationAssociation, order_by=model.HistoryAnnotationAssociation.table.c.id, backref="histories" ),
                     ratings=relation( model.HistoryRatingAssociation, order_by=model.HistoryRatingAssociation.table.c.id, backref="histories" ) )
                      )

# Set up proxy so that
#   History.users_shared_with
# returns a list of users that history is shared with.
model.History.users_shared_with_dot_users = association_proxy( 'users_shared_with', 'user' )

mapper( model.HistoryUserShareAssociation, model.HistoryUserShareAssociation.table,
    properties=dict( user=relation( model.User, backref='histories_shared_by_others' ),
                     history=relation( model.History, backref='users_shared_with' )
                   ) )

mapper( model.User, model.User.table,
    properties=dict( histories=relation( model.History, backref="user",
                                         order_by=desc(model.History.table.c.update_time) ),
                     active_histories=relation( model.History, primaryjoin=( ( model.History.table.c.user_id == model.User.table.c.id ) & ( not_( model.History.table.c.deleted ) ) ), order_by=desc( model.History.table.c.update_time ) ),
                     galaxy_sessions=relation( model.GalaxySession, order_by=desc( model.GalaxySession.table.c.update_time ) ),
                     stored_workflow_menu_entries=relation( model.StoredWorkflowMenuEntry, backref="user",
                                                            cascade="all, delete-orphan",
                                                            collection_class=ordering_list( 'order_index' ) ),
                     _preferences=relation( model.UserPreference, backref="user", collection_class=attribute_mapped_collection('name')),
#                     addresses=relation( UserAddress,
#                                         primaryjoin=( User.table.c.id == UserAddress.table.c.user_id ) )
                     values=relation( model.FormValues,
                                      primaryjoin=( model.User.table.c.form_values_id == model.FormValues.table.c.id ) ),
                     api_keys=relation( model.APIKeys, backref="user", order_by=desc( model.APIKeys.table.c.create_time ) ),
                     ) )

# Set up proxy so that this syntax is possible:
# <user_obj>.preferences[pref_name] = pref_value
model.User.preferences = association_proxy('_preferences', 'value', creator=model.UserPreference)

mapper( model.Group, model.Group.table,
    properties=dict( users=relation( model.UserGroupAssociation ) ) )

mapper( model.UserGroupAssociation, model.UserGroupAssociation.table,
    properties=dict( user=relation( model.User, backref = "groups" ),
                     group=relation( model.Group, backref = "members" ) ) )

mapper( model.DefaultUserPermissions, model.DefaultUserPermissions.table,
    properties=dict( user=relation( model.User, backref = "default_permissions" ),
                     role=relation( model.Role ) ) )

mapper( model.DefaultHistoryPermissions, model.DefaultHistoryPermissions.table,
    properties=dict( history=relation( model.History, backref = "default_permissions" ),
                     role=relation( model.Role ) ) )

mapper( model.Role, model.Role.table,
    properties=dict(
        users=relation( model.UserRoleAssociation ),
        groups=relation( model.GroupRoleAssociation )
    )
)

mapper( model.UserRoleAssociation, model.UserRoleAssociation.table,
    properties=dict(
        user=relation( model.User, backref="roles" ),
        non_private_roles=relation( model.User,
                                    backref="non_private_roles",
                                    primaryjoin=( ( model.User.table.c.id == model.UserRoleAssociation.table.c.user_id ) & ( model.UserRoleAssociation.table.c.role_id == model.Role.table.c.id ) & not_( model.Role.table.c.name == model.User.table.c.email ) ) ),
        role=relation( model.Role )
    )
)

mapper( model.GroupRoleAssociation, model.GroupRoleAssociation.table,
    properties=dict(
        group=relation( model.Group, backref="roles" ),
        role=relation( model.Role )
    )
)

mapper( model.Quota, model.Quota.table,
    properties=dict( users=relation( model.UserQuotaAssociation ),
                     groups=relation( model.GroupQuotaAssociation ) ) )

mapper( model.UserQuotaAssociation, model.UserQuotaAssociation.table,
    properties=dict( user=relation( model.User, backref="quotas" ),
                     quota=relation( model.Quota ) ) )

mapper( model.GroupQuotaAssociation, model.GroupQuotaAssociation.table,
    properties=dict( group=relation( model.Group, backref="quotas" ),
                     quota=relation( model.Quota ) ) )

mapper( model.DefaultQuotaAssociation, model.DefaultQuotaAssociation.table,
    properties=dict( quota=relation( model.Quota, backref="default" ) ) )

mapper( model.DatasetPermissions, model.DatasetPermissions.table,
    properties=dict(
        dataset=relation( model.Dataset, backref="actions" ),
        role=relation( model.Role, backref="dataset_actions" )
    )
)

mapper( model.LibraryPermissions, model.LibraryPermissions.table,
    properties=dict(
        library=relation( model.Library, backref="actions" ),
        role=relation( model.Role, backref="library_actions" )
    )
)

mapper( model.LibraryFolderPermissions, model.LibraryFolderPermissions.table,
    properties=dict(
        folder=relation( model.LibraryFolder, backref="actions" ),
        role=relation( model.Role, backref="library_folder_actions" )
    )
)

mapper( model.LibraryDatasetPermissions, model.LibraryDatasetPermissions.table,
    properties=dict(
        library_dataset=relation( model.LibraryDataset, backref="actions" ),
        role=relation( model.Role, backref="library_dataset_actions" )
    )
)

mapper( model.LibraryDatasetDatasetAssociationPermissions, model.LibraryDatasetDatasetAssociationPermissions.table,
    properties=dict(
        library_dataset_dataset_association = relation( model.LibraryDatasetDatasetAssociation, backref="actions" ),
        role=relation( model.Role, backref="library_dataset_dataset_actions" )
    )
)

mapper( model.Library, model.Library.table,
    properties=dict(
        root_folder=relation( model.LibraryFolder, backref=backref( "library_root" ) )
    )
)

mapper( model.ExtendedMetadata, model.ExtendedMetadata.table,
    properties=dict(
        children=relation(
            model.ExtendedMetadataIndex,
            primaryjoin=( model.ExtendedMetadataIndex.table.c.extended_metadata_id == model.ExtendedMetadata.table.c.id ),
            backref=backref("parent",
                primaryjoin=( model.ExtendedMetadataIndex.table.c.extended_metadata_id == model.ExtendedMetadata.table.c.id )
            )
        )
    )
)

mapper( model.ExtendedMetadataIndex, model.ExtendedMetadataIndex.table,
    properties=dict(
        extended_metadata=relation(
            model.ExtendedMetadata,
            primaryjoin=( ( model.ExtendedMetadataIndex.table.c.extended_metadata_id == model.ExtendedMetadata.table.c.id ) )
        )
    )
)


mapper( model.LibraryInfoAssociation, model.LibraryInfoAssociation.table,
               properties=dict( library=relation( model.Library,
                                                  primaryjoin=( ( model.LibraryInfoAssociation.table.c.library_id == model.Library.table.c.id ) & ( not_( model.LibraryInfoAssociation.table.c.deleted ) ) ), backref="info_association" ),
                                template=relation( model.FormDefinition,
                                                   primaryjoin=( model.LibraryInfoAssociation.table.c.form_definition_id == model.FormDefinition.table.c.id ) ),
                                info=relation( model.FormValues,
                                               primaryjoin=( model.LibraryInfoAssociation.table.c.form_values_id == model.FormValues.table.c.id ) )
                              ) )

mapper( model.LibraryFolder, model.LibraryFolder.table,
    properties=dict(
        folders=relation(
            model.LibraryFolder,
            primaryjoin=( model.LibraryFolder.table.c.parent_id == model.LibraryFolder.table.c.id ),
            order_by=asc( model.LibraryFolder.table.c.name ),
            backref=backref( "parent", primaryjoin=( model.LibraryFolder.table.c.parent_id == model.LibraryFolder.table.c.id ), remote_side=[model.LibraryFolder.table.c.id] ) ),
        active_folders=relation( model.LibraryFolder,
            primaryjoin=( ( model.LibraryFolder.table.c.parent_id == model.LibraryFolder.table.c.id ) & ( not_( model.LibraryFolder.table.c.deleted ) ) ),
            order_by=asc( model.LibraryFolder.table.c.name ),
            lazy=True, #"""sqlalchemy.exceptions.ArgumentError: Error creating eager relationship 'active_folders' on parent class '<class 'galaxy.model.LibraryFolder'>' to child class '<class 'galaxy.model.LibraryFolder'>': Cant use eager loading on a self referential relationship."""
            viewonly=True ),
        datasets=relation( model.LibraryDataset,
            primaryjoin=( ( model.LibraryDataset.table.c.folder_id == model.LibraryFolder.table.c.id ) ),
            order_by=asc( model.LibraryDataset.table.c._name ),
            lazy=True,
            viewonly=True ),
        active_datasets=relation( model.LibraryDataset,
            primaryjoin=( ( model.LibraryDataset.table.c.folder_id == model.LibraryFolder.table.c.id ) & ( not_( model.LibraryDataset.table.c.deleted ) ) ),
            order_by=asc( model.LibraryDataset.table.c._name ),
            lazy=True,
            viewonly=True )
    ) )

mapper( model.LibraryFolderInfoAssociation, model.LibraryFolderInfoAssociation.table,
               properties=dict( folder=relation( model.LibraryFolder,
                                                 primaryjoin=( ( model.LibraryFolderInfoAssociation.table.c.library_folder_id == model.LibraryFolder.table.c.id ) & ( not_( model.LibraryFolderInfoAssociation.table.c.deleted ) ) ), backref="info_association" ),
                                template=relation( model.FormDefinition,
                                                   primaryjoin=( model.LibraryFolderInfoAssociation.table.c.form_definition_id == model.FormDefinition.table.c.id ) ),
                                info=relation( model.FormValues,
                                               primaryjoin=( model.LibraryFolderInfoAssociation.table.c.form_values_id == model.FormValues.table.c.id ) )
                              ) )

mapper( model.LibraryDataset, model.LibraryDataset.table,
    properties=dict(
        folder=relation( model.LibraryFolder ),
        library_dataset_dataset_association=relation( model.LibraryDatasetDatasetAssociation, primaryjoin=( model.LibraryDataset.table.c.library_dataset_dataset_association_id == model.LibraryDatasetDatasetAssociation.table.c.id ) ),
        expired_datasets = relation( model.LibraryDatasetDatasetAssociation, foreign_keys=[model.LibraryDataset.table.c.id,model.LibraryDataset.table.c.library_dataset_dataset_association_id ], primaryjoin=( ( model.LibraryDataset.table.c.id == model.LibraryDatasetDatasetAssociation.table.c.library_dataset_id ) & ( not_( model.LibraryDataset.table.c.library_dataset_dataset_association_id == model.LibraryDatasetDatasetAssociation.table.c.id ) ) ), viewonly=True, uselist=True )
        ) )

mapper( model.LibraryDatasetDatasetAssociation, model.LibraryDatasetDatasetAssociation.table,
    properties=dict(
        dataset=relation( model.Dataset ),
        library_dataset = relation( model.LibraryDataset,
        primaryjoin=( model.LibraryDatasetDatasetAssociation.table.c.library_dataset_id == model.LibraryDataset.table.c.id ) ),
        #user=relation( model.User.mapper ),
        user=relation( model.User ),
        copied_from_library_dataset_dataset_association=relation(
            model.LibraryDatasetDatasetAssociation,
            primaryjoin=( model.LibraryDatasetDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id == model.LibraryDatasetDatasetAssociation.table.c.id ),
            remote_side=[model.LibraryDatasetDatasetAssociation.table.c.id],
            uselist=False ),
        copied_to_library_dataset_dataset_associations=relation(
            model.LibraryDatasetDatasetAssociation,
            primaryjoin=( model.LibraryDatasetDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id == model.LibraryDatasetDatasetAssociation.table.c.id ) ),
        copied_from_history_dataset_association=relation(
            model.HistoryDatasetAssociation,
            primaryjoin=( model.LibraryDatasetDatasetAssociation.table.c.copied_from_history_dataset_association_id == model.HistoryDatasetAssociation.table.c.id  ),
            uselist=False ),
        copied_to_history_dataset_associations=relation(
            model.HistoryDatasetAssociation,
            primaryjoin=( model.HistoryDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id == model.LibraryDatasetDatasetAssociation.table.c.id ) ),
        implicitly_converted_datasets=relation(
            model.ImplicitlyConvertedDatasetAssociation,
            primaryjoin=( model.ImplicitlyConvertedDatasetAssociation.table.c.ldda_parent_id == model.LibraryDatasetDatasetAssociation.table.c.id ) ),
        children=relation(
            model.LibraryDatasetDatasetAssociation,
            primaryjoin=( model.LibraryDatasetDatasetAssociation.table.c.parent_id == model.LibraryDatasetDatasetAssociation.table.c.id ),
            backref=backref( "parent", primaryjoin=( model.LibraryDatasetDatasetAssociation.table.c.parent_id == model.LibraryDatasetDatasetAssociation.table.c.id ), remote_side=[model.LibraryDatasetDatasetAssociation.table.c.id] ) ),
        visible_children=relation(
            model.LibraryDatasetDatasetAssociation,
            primaryjoin=( ( model.LibraryDatasetDatasetAssociation.table.c.parent_id == model.LibraryDatasetDatasetAssociation.table.c.id ) & ( model.LibraryDatasetDatasetAssociation.table.c.visible == True ) ) ),
        extended_metadata=relation(
            model.ExtendedMetadata,
            primaryjoin=( ( model.LibraryDatasetDatasetAssociation.table.c.extended_metadata_id == model.ExtendedMetadata.table.c.id ) )
        )
    ))

mapper( model.LibraryDatasetDatasetInfoAssociation, model.LibraryDatasetDatasetInfoAssociation.table,
               properties=dict( library_dataset_dataset_association=relation( model.LibraryDatasetDatasetAssociation,
                                                                              primaryjoin=( ( model.LibraryDatasetDatasetInfoAssociation.table.c.library_dataset_dataset_association_id == model.LibraryDatasetDatasetAssociation.table.c.id ) & ( not_( model.LibraryDatasetDatasetInfoAssociation.table.c.deleted ) ) ), backref="info_association" ),
                                template=relation( model.FormDefinition,
                                                   primaryjoin=( model.LibraryDatasetDatasetInfoAssociation.table.c.form_definition_id == model.FormDefinition.table.c.id ) ),
                                info=relation( model.FormValues,
                                               primaryjoin=( model.LibraryDatasetDatasetInfoAssociation.table.c.form_values_id == model.FormValues.table.c.id ) )
                              ) )

mapper( model.JobToInputDatasetAssociation,
        model.JobToInputDatasetAssociation.table, properties=dict(
            job=relation( model.Job ), dataset=relation(
                model.HistoryDatasetAssociation, lazy=False,
                backref="dependent_jobs" ) ) )

mapper( model.JobToOutputDatasetAssociation,
        model.JobToOutputDatasetAssociation.table, properties=dict(
            job=relation( model.Job ), dataset=relation(
                model.HistoryDatasetAssociation, lazy=False ) ) )

mapper( model.JobToInputDatasetCollectionAssociation,
        model.JobToInputDatasetCollectionAssociation.table, properties=dict(
            job=relation( model.Job ), dataset_collection=relation(
                model.HistoryDatasetCollectionAssociation, lazy=False,
                backref="dependent_jobs" ) ) )

mapper( model.JobToOutputDatasetCollectionAssociation,
        model.JobToOutputDatasetCollectionAssociation.table, properties=dict(
            job=relation( model.Job ), dataset_collection=relation(
                model.HistoryDatasetCollectionAssociation, lazy=False ) ) )

mapper( model.JobToInputLibraryDatasetAssociation,
        model.JobToInputLibraryDatasetAssociation.table, properties=dict(
            job=relation( model.Job ), dataset=relation(
                model.LibraryDatasetDatasetAssociation, lazy=False,
                backref="dependent_jobs" ) ) )

mapper( model.JobToOutputLibraryDatasetAssociation,
        model.JobToOutputLibraryDatasetAssociation.table, properties=dict(
            job=relation( model.Job ), dataset=relation(
                model.LibraryDatasetDatasetAssociation, lazy=False ) ) )

simple_mapping(
    model.JobMetricText,
    job=relation( model.Job, backref="text_metrics" ),
)

simple_mapping(
    model.TaskMetricText,
    task=relation( model.Task, backref="text_metrics" ),
)

simple_mapping(
    model.JobMetricNumeric,
    job=relation( model.Job, backref="numeric_metrics" ),
)

simple_mapping(
    model.TaskMetricNumeric,
    task=relation( model.Task, backref="numeric_metrics" ),
)

simple_mapping(
    model.ImplicitlyCreatedDatasetCollectionInput,
    input_dataset_collection=relation(
        model.HistoryDatasetCollectionAssociation,
        primaryjoin=( ( model.HistoryDatasetCollectionAssociation.table.c.id == model.ImplicitlyCreatedDatasetCollectionInput.table.c.input_dataset_collection_id ) ),
        # backref="implicitly_created_dataset_collections",
    ),
)

mapper( model.JobParameter, model.JobParameter.table )

mapper( model.JobExternalOutputMetadata, model.JobExternalOutputMetadata.table,
    properties=dict( job = relation( model.Job ),
                     history_dataset_association = relation( model.HistoryDatasetAssociation, lazy = False ),
                     library_dataset_dataset_association = relation( model.LibraryDatasetDatasetAssociation, lazy = False ) ) )

mapper( model.JobExportHistoryArchive, model.JobExportHistoryArchive.table,
    properties=dict( job = relation( model.Job ),
                     history = relation( model.History ),
                     dataset = relation( model.Dataset ) ) )

mapper( model.JobImportHistoryArchive, model.JobImportHistoryArchive.table,
    properties=dict( job = relation( model.Job ), history = relation( model.History ) ) )

mapper( model.GenomeIndexToolData, model.GenomeIndexToolData.table,
    properties=dict( job = relation( model.Job, backref='job' ),
                     dataset = relation( model.Dataset ),
                     user = relation( model.User ),
                     deferred = relation( model.DeferredJob, backref='deferred_job' ),
                     transfer = relation( model.TransferJob, backref='transfer_job' ) ) )

mapper(model.PostJobAction, model.PostJobAction.table,
    properties=dict(workflow_step = relation( model.WorkflowStep, backref='post_job_actions', primaryjoin=(model.WorkflowStep.table.c.id == model.PostJobAction.table.c.workflow_step_id))))

mapper( model.PostJobActionAssociation, model.PostJobActionAssociation.table,
    properties=dict( job = relation( model.Job ),
                     post_job_action = relation( model.PostJobAction) ) )

mapper( model.Job, model.Job.table,
    #properties=dict( user=relation( model.User.mapper ),
    properties=dict( user=relation( model.User ),
                     galaxy_session=relation( model.GalaxySession ),
                     history=relation( model.History ),
                     library_folder=relation( model.LibraryFolder ),
                     parameters=relation( model.JobParameter, lazy=False ),
                     input_datasets=relation( model.JobToInputDatasetAssociation ),
                     output_datasets=relation( model.JobToOutputDatasetAssociation ),
                     post_job_actions=relation( model.PostJobActionAssociation, lazy=False ),
                     input_library_datasets=relation( model.JobToInputLibraryDatasetAssociation ),
                     output_library_datasets=relation( model.JobToOutputLibraryDatasetAssociation ),
                     external_output_metadata = relation( model.JobExternalOutputMetadata, lazy = False ),
                     tasks = relation(model.Task) ) )

mapper( model.Task, model.Task.table,
    properties=dict( job = relation( model.Job ) ) )

mapper( model.DeferredJob, model.DeferredJob.table,
    properties = {} )

mapper( model.TransferJob, model.TransferJob.table,
    properties = {} )


simple_mapping( model.DatasetCollection,
    elements=relation(
        model.DatasetCollectionElement,
        primaryjoin=( model.DatasetCollection.table.c.id == model.DatasetCollectionElement.table.c.dataset_collection_id ),
        remote_side=[ model.DatasetCollectionElement.table.c.dataset_collection_id ],
        backref="collection",
        order_by=model.DatasetCollectionElement.table.c.element_index,
    ),
)

simple_mapping( model.HistoryDatasetCollectionAssociation,
    collection=relation( model.DatasetCollection ),
    history=relation( model.History, backref='dataset_collections' ),
    copied_from_history_dataset_collection_association=relation(
        model.HistoryDatasetCollectionAssociation,
        primaryjoin=( model.HistoryDatasetCollectionAssociation.table.c.copied_from_history_dataset_collection_association_id == model.HistoryDatasetCollectionAssociation.table.c.id ),
        remote_side=[model.HistoryDatasetCollectionAssociation.table.c.id],
        uselist=False ),
    copied_to_history_dataset_collection_associations=relation(
        model.HistoryDatasetCollectionAssociation,
        primaryjoin=( model.HistoryDatasetCollectionAssociation.table.c.copied_from_history_dataset_collection_association_id == model.HistoryDatasetCollectionAssociation.table.c.id ) ),
    implicit_input_collections=relation(
        model.ImplicitlyCreatedDatasetCollectionInput,
        primaryjoin=( ( model.HistoryDatasetCollectionAssociation.table.c.id == model.ImplicitlyCreatedDatasetCollectionInput.table.c.dataset_collection_id ) ),
        backref="dataset_collection",
    ),
    tags=relation( model.HistoryDatasetCollectionTagAssociation, order_by=model.HistoryDatasetCollectionTagAssociation.table.c.id, backref='dataset_collections' ),
    annotations=relation( model.HistoryDatasetCollectionAnnotationAssociation, order_by=model.HistoryDatasetCollectionAnnotationAssociation.table.c.id, backref="dataset_collections" ),
    ratings=relation( model.HistoryDatasetCollectionRatingAssociation, order_by=model.HistoryDatasetCollectionRatingAssociation.table.c.id, backref="dataset_collections" ),
)

simple_mapping( model.LibraryDatasetCollectionAssociation,
    collection=relation( model.DatasetCollection ),
    folder=relation( model.LibraryFolder, backref='dataset_collections' ),
    tags=relation( model.LibraryDatasetCollectionTagAssociation, order_by=model.LibraryDatasetCollectionTagAssociation.table.c.id, backref='dataset_collections' ),
    annotations=relation( model.LibraryDatasetCollectionAnnotationAssociation, order_by=model.LibraryDatasetCollectionAnnotationAssociation.table.c.id, backref="dataset_collections" ),
    ratings=relation( model.LibraryDatasetCollectionRatingAssociation, order_by=model.LibraryDatasetCollectionRatingAssociation.table.c.id, backref="dataset_collections" ),
)

simple_mapping( model.DatasetCollectionElement,
    hda=relation(
        model.HistoryDatasetAssociation,
        primaryjoin=( model.DatasetCollectionElement.table.c.hda_id == model.HistoryDatasetAssociation.table.c.id )
    ),
    ldda=relation(
        model.LibraryDatasetDatasetAssociation,
        primaryjoin=( model.DatasetCollectionElement.table.c.ldda_id == model.LibraryDatasetDatasetAssociation.table.c.id )
    ),
    child_collection=relation(
        model.DatasetCollection,
        primaryjoin=( model.DatasetCollectionElement.table.c.child_collection_id == model.DatasetCollection.table.c.id ),
    ),
)

mapper( model.Event, model.Event.table,
    properties=dict( history=relation( model.History ),
                     galaxy_session=relation( model.GalaxySession ),
                     #user=relation( model.User.mapper ) ) )
                     user=relation( model.User ) ) )

mapper( model.GalaxySession, model.GalaxySession.table,
    properties=dict( histories=relation( model.GalaxySessionToHistoryAssociation ),
                     current_history=relation( model.History ),
                     #user=relation( model.User.mapper ) ) )
                     user=relation( model.User ) ) )

mapper( model.GalaxySessionToHistoryAssociation, model.GalaxySessionToHistoryAssociation.table,
    properties=dict( galaxy_session=relation( model.GalaxySession ),
                     history=relation( model.History ) ) )

mapper( model.Workflow, model.Workflow.table,
    properties=dict( steps=relation( model.WorkflowStep, backref='workflow',
                                     order_by=asc(model.WorkflowStep.table.c.order_index),
                                     cascade="all, delete-orphan",
                                     lazy=False ),
                     ) )

mapper( model.WorkflowStep, model.WorkflowStep.table,
                properties=dict(
                    tags=relation(model.WorkflowStepTagAssociation, order_by=model.WorkflowStepTagAssociation.table.c.id, backref="workflow_steps"),
                    annotations=relation( model.WorkflowStepAnnotationAssociation, order_by=model.WorkflowStepAnnotationAssociation.table.c.id, backref="workflow_steps" ) )
                )

mapper( model.WorkflowOutput, model.WorkflowOutput.table,
    properties=dict(workflow_step = relation( model.WorkflowStep, backref='workflow_outputs', primaryjoin=(model.WorkflowStep.table.c.id == model.WorkflowOutput.table.c.workflow_step_id))))

mapper( model.WorkflowStepConnection, model.WorkflowStepConnection.table,
    properties=dict( input_step=relation( model.WorkflowStep, backref="input_connections", cascade="all",
                                          primaryjoin=( model.WorkflowStepConnection.table.c.input_step_id == model.WorkflowStep.table.c.id ) ),
                     output_step=relation( model.WorkflowStep, backref="output_connections", cascade="all",
                                           primaryjoin=( model.WorkflowStepConnection.table.c.output_step_id == model.WorkflowStep.table.c.id ) ) ) )


mapper( model.StoredWorkflow, model.StoredWorkflow.table,
    properties=dict( user=relation( model.User,
                                    primaryjoin=( model.User.table.c.id == model.StoredWorkflow.table.c.user_id ),
                                    backref='stored_workflows' ),
                     workflows=relation( model.Workflow, backref='stored_workflow',
                                         cascade="all, delete-orphan",
                                         primaryjoin=( model.StoredWorkflow.table.c.id == model.Workflow.table.c.stored_workflow_id ) ),
                     latest_workflow=relation( model.Workflow, post_update=True,
                                               primaryjoin=( model.StoredWorkflow.table.c.latest_workflow_id == model.Workflow.table.c.id ),
                                               lazy=False ),
                     tags=relation( model.StoredWorkflowTagAssociation, order_by=model.StoredWorkflowTagAssociation.table.c.id, backref="stored_workflows" ),
                     owner_tags=relation( model.StoredWorkflowTagAssociation,
                                    primaryjoin=and_( model.StoredWorkflow.table.c.id == model.StoredWorkflowTagAssociation.table.c.stored_workflow_id,
                                                      model.StoredWorkflow.table.c.user_id == model.StoredWorkflowTagAssociation.table.c.user_id ),
                                    order_by=model.StoredWorkflowTagAssociation.table.c.id ),
                     annotations=relation( model.StoredWorkflowAnnotationAssociation, order_by=model.StoredWorkflowAnnotationAssociation.table.c.id, backref="stored_workflows" ),
                     ratings=relation( model.StoredWorkflowRatingAssociation, order_by=model.StoredWorkflowRatingAssociation.table.c.id, backref="stored_workflows" ) )
                   )

# Set up proxy so that
#   StoredWorkflow.users_shared_with
# returns a list of users that workflow is shared with.
model.StoredWorkflow.users_shared_with_dot_users = association_proxy( 'users_shared_with', 'user' )

mapper( model.StoredWorkflowUserShareAssociation, model.StoredWorkflowUserShareAssociation.table,
    properties=dict( user=relation( model.User, backref='workflows_shared_by_others' ),
                     stored_workflow=relation( model.StoredWorkflow, backref='users_shared_with' )
                   ) )

mapper( model.StoredWorkflowMenuEntry, model.StoredWorkflowMenuEntry.table,
    properties=dict( stored_workflow=relation( model.StoredWorkflow ) ) )

mapper( model.WorkflowInvocation, model.WorkflowInvocation.table,
    properties=dict(
        steps=relation( model.WorkflowInvocationStep, backref='workflow_invocation', lazy=False ),
        workflow=relation( model.Workflow ) ) )

mapper( model.WorkflowInvocationStep, model.WorkflowInvocationStep.table,
    properties=dict(
        workflow_step = relation( model.WorkflowStep ),
        job = relation( model.Job, backref=backref( 'workflow_invocation_step', uselist=False ) ) ) )

mapper( model.MetadataFile, model.MetadataFile.table,
    properties=dict( history_dataset=relation( model.HistoryDatasetAssociation ), library_dataset=relation( model.LibraryDatasetDatasetAssociation ) ) )

mapper( model.PageRevision, model.PageRevision.table )

mapper( model.Page, model.Page.table,
    properties=dict( user=relation( model.User ),
                     revisions=relation( model.PageRevision, backref='page',
                                         cascade="all, delete-orphan",
                                         primaryjoin=( model.Page.table.c.id == model.PageRevision.table.c.page_id ) ),
                     latest_revision=relation( model.PageRevision, post_update=True,
                                               primaryjoin=( model.Page.table.c.latest_revision_id == model.PageRevision.table.c.id ),
                                               lazy=False ),
                     tags=relation(model.PageTagAssociation, order_by=model.PageTagAssociation.table.c.id, backref="pages"),
                     annotations=relation( model.PageAnnotationAssociation, order_by=model.PageAnnotationAssociation.table.c.id, backref="pages" ),
                     ratings=relation( model.PageRatingAssociation, order_by=model.PageRatingAssociation.table.c.id, backref="pages" )
                   ) )

# Set up proxy so that
#   Page.users_shared_with
# returns a list of users that page is shared with.
model.Page.users_shared_with_dot_users = association_proxy( 'users_shared_with', 'user' )

mapper( model.PageUserShareAssociation, model.PageUserShareAssociation.table,
   properties=dict( user=relation( model.User, backref='pages_shared_by_others' ),
                    page=relation( model.Page, backref='users_shared_with' )
                  ) )

mapper( model.VisualizationRevision, model.VisualizationRevision.table )

mapper( model.Visualization, model.Visualization.table,
    properties=dict( user=relation( model.User ),
                     revisions=relation( model.VisualizationRevision, backref='visualization',
                                         cascade="all, delete-orphan",
                                         primaryjoin=( model.Visualization.table.c.id == model.VisualizationRevision.table.c.visualization_id ) ),
                     latest_revision=relation( model.VisualizationRevision, post_update=True,
                                               primaryjoin=( model.Visualization.table.c.latest_revision_id == model.VisualizationRevision.table.c.id ),
                                               lazy=False ),
                     tags=relation( model.VisualizationTagAssociation, order_by=model.VisualizationTagAssociation.table.c.id, backref="visualizations" ),
                     annotations=relation( model.VisualizationAnnotationAssociation, order_by=model.VisualizationAnnotationAssociation.table.c.id, backref="visualizations" ),
                     ratings=relation( model.VisualizationRatingAssociation, order_by=model.VisualizationRatingAssociation.table.c.id, backref="visualizations" )
                   ) )

# Set up proxy so that
#   Visualization.users_shared_with
# returns a list of users that visualization is shared with.
model.Visualization.users_shared_with_dot_users = association_proxy( 'users_shared_with', 'user' )

mapper( model.VisualizationUserShareAssociation, model.VisualizationUserShareAssociation.table,
  properties=dict( user=relation( model.User, backref='visualizations_shared_by_others' ),
                   visualization=relation( model.Visualization, backref='users_shared_with' )
                 ) )

# Tag tables.
simple_mapping( model.Tag,
    children=relation(model.Tag, backref=backref( 'parent', remote_side=[model.Tag.table.c.id] ) )
)


def tag_mapping( tag_association_class, backref_name ):
    simple_mapping( tag_association_class, tag=relation( model.Tag, backref=backref_name), user=relation( model.User ) )

tag_mapping( model.HistoryTagAssociation, "tagged_histories" )

tag_mapping( model.DatasetTagAssociation, "tagged_datasets" )

tag_mapping( model.HistoryDatasetAssociationTagAssociation, "tagged_history_dataset_associations" )

tag_mapping( model.PageTagAssociation, "tagged_pages" )

tag_mapping( model.StoredWorkflowTagAssociation, "tagged_workflows" )

tag_mapping( model.WorkflowStepTagAssociation, "tagged_workflow_steps" )

tag_mapping( model.VisualizationTagAssociation, "tagged_visualizations" )

tag_mapping( model.HistoryDatasetCollectionTagAssociation, "tagged_history_dataset_collections" )

tag_mapping( model.LibraryDatasetCollectionTagAssociation, "tagged_library_dataset_collections" )

tag_mapping( model.ToolTagAssociation, "tagged_tools" )


# Annotation tables.
def annotation_mapping( annotation_class, **kwds ):
    kwds = dict( [ (key, relation( value ) ) for key, value in kwds.iteritems() ] )
    simple_mapping( annotation_class, **dict(user=relation( model.User ), **kwds ) )

annotation_mapping( model.HistoryAnnotationAssociation, history=model.History )

annotation_mapping( model.HistoryDatasetAssociationAnnotationAssociation, hda=model.HistoryDatasetAssociation )

annotation_mapping( model.StoredWorkflowAnnotationAssociation, stored_workflow=model.StoredWorkflow )

annotation_mapping( model.WorkflowStepAnnotationAssociation, workflow_step=model.WorkflowStep )

annotation_mapping( model.PageAnnotationAssociation, page=model.Page )

annotation_mapping( model.VisualizationAnnotationAssociation, visualization=model.Visualization )

annotation_mapping( model.HistoryDatasetCollectionAnnotationAssociation, history_dataset_collection=model.HistoryDatasetCollectionAssociation )

annotation_mapping( model.LibraryDatasetCollectionAnnotationAssociation, library_dataset_collection=model.LibraryDatasetCollectionAssociation )


# Rating tables.
def rating_mapping( rating_class, **kwds ):
    kwds = dict( [ (key, relation( value ) ) for key, value in kwds.iteritems() ] )
    simple_mapping( rating_class, **dict(user=relation( model.User ), **kwds ) )

rating_mapping( model.HistoryRatingAssociation, history=model.History )

rating_mapping( model.HistoryDatasetAssociationRatingAssociation, hda=model.HistoryDatasetAssociation )

rating_mapping( model.StoredWorkflowRatingAssociation, stored_workflow=model.StoredWorkflow )

rating_mapping( model.PageRatingAssociation, page=model.Page )

rating_mapping( model.VisualizationRatingAssociation, visualizaiton=model.Visualization )

rating_mapping( model.HistoryDatasetCollectionRatingAssociation, history_dataset_collection=model.HistoryDatasetCollectionAssociation )

rating_mapping( model.LibraryDatasetCollectionRatingAssociation, libary_dataset_collection=model.LibraryDatasetCollectionAssociation )

#Data Manager tables
mapper( model.DataManagerHistoryAssociation, model.DataManagerHistoryAssociation.table,
    properties=dict( history=relation( model.History ),
                     user=relation( model.User, backref='data_manager_histories' )
                    )
              )

mapper( model.DataManagerJobAssociation, model.DataManagerJobAssociation.table,
    properties=dict( job=relation( model.Job, backref=backref('data_manager_association', uselist=False ), uselist=False ) )
              )

# User tables.

mapper( model.UserPreference, model.UserPreference.table,
    properties = {}
              )

mapper( model.UserAction, model.UserAction.table,
  #properties = dict( user=relation( model.User.mapper ) )
  properties = dict( user=relation( model.User ) )
            )

mapper( model.APIKeys, model.APIKeys.table,
    properties = {} )


#model.HistoryDatasetAssociation.mapper.add_property( "creating_job_associations", relation( model.JobToOutputDatasetAssociation ) )
#model.LibraryDatasetDatasetAssociation.mapper.add_property( "creating_job_associations", relation( model.JobToOutputLibraryDatasetAssociation ) )
class_mapper(model.HistoryDatasetAssociation).add_property( "creating_job_associations", relation( model.JobToOutputDatasetAssociation ) )
class_mapper(model.LibraryDatasetDatasetAssociation).add_property( "creating_job_associations", relation( model.JobToOutputLibraryDatasetAssociation ) )

class_mapper(model.HistoryDatasetCollectionAssociation).add_property( "creating_job_associations", relation( model.JobToOutputDatasetCollectionAssociation ) )

# Helper methods.

def db_next_hid( self ):
    """
    db_next_hid( self )

    Override __next_hid to generate from the database in a concurrency safe way.
    Loads the next history ID from the DB and returns it.
    It also saves the future next_id into the DB.

    :rtype:     int
    :returns:   the next history id
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

model.History._next_hid = db_next_hid


def init( file_path, url, engine_options={}, create_tables=False, map_install_models=False, database_query_profiling_proxy=False, object_store=None, trace_logger=None, use_pbkdf2=True ):
    """Connect mappings to the database"""
    # Connect dataset to the file path
    model.Dataset.file_path = file_path
    # Connect dataset to object store
    model.Dataset.object_store = object_store
    # Use PBKDF2 password hashing?
    model.User.use_pbkdf2 = use_pbkdf2
    # Load the appropriate db module
    engine = build_engine( url, engine_options, database_query_profiling_proxy, trace_logger )

    # Connect the metadata to the database.
    metadata.bind = engine

    model_modules = [model]
    if map_install_models:
        import galaxy.model.tool_shed_install.mapping
        from galaxy.model import tool_shed_install
        model_modules.append(tool_shed_install)

    result = ModelMapping(model_modules, engine=engine)

    # Create tables if needed
    if create_tables:
        metadata.create_all()
        # metadata.engine.commit()

    result.create_tables = create_tables
    #load local galaxy security policy
    result.security_agent = GalaxyRBACAgent( result )
    return result
