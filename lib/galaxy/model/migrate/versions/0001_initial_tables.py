import datetime
import logging

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, Numeric, String, Table, TEXT

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import JSONType, MetadataType, TrimmedString

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
metadata = MetaData()

# Tables as of changeset 1464:c7acaa1bb88f
User_table = Table( "galaxy_user", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "email", TrimmedString( 255 ), nullable=False ),
    Column( "password", TrimmedString( 40 ), nullable=False ),
    Column( "external", Boolean, default=False ) )

History_table = Table( "history", metadata,
    Column( "id", Integer, primary_key=True),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "name", TrimmedString( 255 ) ),
    Column( "hid_counter", Integer, default=1 ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ),
    Column( "genome_build", TrimmedString( 40 ) ) )

HistoryDatasetAssociation_table = Table( "history_dataset_association", metadata,
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
    Column( "peek", TEXT ),
    Column( "extension", TrimmedString( 64 ) ),
    Column( "metadata", MetadataType(), key="_metadata" ),
    Column( "parent_id", Integer, ForeignKey( "history_dataset_association.id" ), nullable=True ),
    Column( "designation", TrimmedString( 255 ) ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "visible", Boolean ) )

Dataset_table = Table( "dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "state", TrimmedString( 64 ) ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ),
    Column( "purgable", Boolean, default=True ),
    Column( "external_filename", TEXT ),
    Column( "_extra_files_path", TEXT ),
    Column( 'file_size', Numeric( 15, 0 ) ) )

ImplicitlyConvertedDatasetAssociation_table = Table( "implicitly_converted_dataset_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "hda_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True, nullable=True ),
    Column( "hda_parent_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "metadata_safe", Boolean, index=True, default=True ),
    Column( "type", TrimmedString( 255 ) ) )

ValidationError_table = Table( "validation_error", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "dataset_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "message", TrimmedString( 255 ) ),
    Column( "err_type", TrimmedString( 64 ) ),
    Column( "attributes", TEXT ) )

Job_table = Table( "job", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "tool_id", String( 255 ) ),
    Column( "tool_version", TEXT, default="1.0.0" ),
    Column( "state", String( 64 ) ),
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

JobParameter_table = Table( "job_parameter", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "name", String(255) ),
    Column( "value", TEXT ) )

JobToInputDatasetAssociation_table = Table( "job_to_input_dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "name", String(255) ) )

JobToOutputDatasetAssociation_table = Table( "job_to_output_dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True ),
    Column( "name", String(255) ) )

Event_table = Table( "event", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True, nullable=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=True ),
    Column( "message", TrimmedString( 1024 ) ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), index=True, nullable=True ),
    Column( "tool_id", String( 255 ) ) )

GalaxySession_table = Table( "galaxy_session", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=True ),
    Column( "remote_host", String( 255 ) ),
    Column( "remote_addr", String( 255 ) ),
    Column( "referer", TEXT ),
    Column( "current_history_id", Integer, ForeignKey( "history.id" ), nullable=True ),
    Column( "session_key", TrimmedString( 255 ), index=True, unique=True ),
    Column( "is_valid", Boolean, default=False ),
    Column( "prev_session_id", Integer ) )

GalaxySessionToHistoryAssociation_table = Table( "galaxy_session_to_history", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "session_id", Integer, ForeignKey( "galaxy_session.id" ), index=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ) )

StoredWorkflow_table = Table( "stored_workflow", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True, nullable=False ),
    Column( "latest_workflow_id", Integer,
            ForeignKey( "workflow.id", use_alter=True, name='stored_workflow_latest_workflow_id_fk' ), index=True ),
    Column( "name", TEXT ),
    Column( "deleted", Boolean, default=False ) )

Workflow_table = Table( "workflow", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True, nullable=False ),
    Column( "name", TEXT ),
    Column( "has_cycles", Boolean ),
    Column( "has_errors", Boolean ) )

WorkflowStep_table = Table( "workflow_step", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "workflow_id", Integer, ForeignKey( "workflow.id" ), index=True, nullable=False ),
    Column( "type", String(64) ),
    Column( "tool_id", TEXT ),
    Column( "tool_version", TEXT ),
    Column( "tool_inputs", JSONType ),
    Column( "tool_errors", JSONType ),
    Column( "position", JSONType ),
    Column( "config", JSONType ),
    Column( "order_index", Integer ) )

WorkflowStepConnection_table = Table( "workflow_step_connection", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "output_step_id", Integer, ForeignKey( "workflow_step.id" ), index=True ),
    Column( "input_step_id", Integer, ForeignKey( "workflow_step.id" ), index=True ),
    Column( "output_name", TEXT ),
    Column( "input_name", TEXT) )

StoredWorkflowUserShareAssociation_table = Table( "stored_workflow_user_share_connection", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ) )

StoredWorkflowMenuEntry_table = Table( "stored_workflow_menu_entry", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "stored_workflow_id", Integer, ForeignKey( "stored_workflow.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "order_index", Integer ) )


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.create_all()
