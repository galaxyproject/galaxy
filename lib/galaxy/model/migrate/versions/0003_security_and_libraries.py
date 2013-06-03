from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import *
from migrate import *
from migrate.changeset import *

import datetime
now = datetime.datetime.utcnow

import sys, logging
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

metadata = MetaData()

# New tables as of changeset 2341:5498ac35eedd
Group_table = Table( "galaxy_group", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", String( 255 ), index=True, unique=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

UserGroupAssociation_table = Table( "user_group_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "group_id", Integer, ForeignKey( "galaxy_group.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

UserRoleAssociation_table = Table( "user_role_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

GroupRoleAssociation_table = Table( "group_role_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "group_id", Integer, ForeignKey( "galaxy_group.id" ), index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ) )

Role_table = Table( "role", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", String( 255 ), index=True, unique=True ),
    Column( "description", TEXT ),
    Column( "type", String( 40 ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ) )

DatasetPermissions_table = Table( "dataset_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

LibraryPermissions_table = Table( "library_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "library_id", Integer, ForeignKey( "library.id" ), nullable=True, index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

LibraryFolderPermissions_table = Table( "library_folder_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "library_folder_id", Integer, ForeignKey( "library_folder.id" ), nullable=True, index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

LibraryDatasetPermissions_table = Table( "library_dataset_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "library_dataset_id", Integer, ForeignKey( "library_dataset.id" ), nullable=True, index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

LibraryDatasetDatasetAssociationPermissions_table = Table( "library_dataset_dataset_association_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), nullable=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )
Index( "ix_lddap_library_dataset_dataset_association_id", LibraryDatasetDatasetAssociationPermissions_table.c.library_dataset_dataset_association_id )

LibraryItemInfoPermissions_table = Table( "library_item_info_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "library_item_info_id", Integer, ForeignKey( "library_item_info.id" ), nullable=True, index=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

LibraryItemInfoTemplatePermissions_table = Table( "library_item_info_template_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "action", TEXT ),
    Column( "library_item_info_template_id", Integer, ForeignKey( "library_item_info_template.id" ), nullable=True ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )
Index( "ix_liitp_library_item_info_template_id", LibraryItemInfoTemplatePermissions_table.c.library_item_info_template_id )

DefaultUserPermissions_table = Table( "default_user_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), index=True ),
    Column( "action", TEXT ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

DefaultHistoryPermissions_table = Table( "default_history_permissions", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "history_id", Integer, ForeignKey( "history.id" ), index=True ),
    Column( "action", TEXT ),
    Column( "role_id", Integer, ForeignKey( "role.id" ), index=True ) )

LibraryDataset_table = Table( "library_dataset", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id", use_alter=True, name="library_dataset_dataset_association_id_fk" ), nullable=True, index=True ),#current version of dataset, if null, there is not a current version selected
    Column( "folder_id", Integer, ForeignKey( "library_folder.id" ), index=True ),
    Column( "order_id", Integer ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), key="_name" ), #when not None/null this will supercede display in library (but not when imported into user's history?)
    Column( "info", TrimmedString( 255 ),  key="_info" ), #when not None/null this will supercede display in library (but not when imported into user's history?)
    Column( "deleted", Boolean, index=True, default=False ) )

LibraryDatasetDatasetAssociation_table = Table( "library_dataset_dataset_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "library_dataset_id", Integer, ForeignKey( "library_dataset.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "copied_from_history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id", use_alter=True, name='history_dataset_association_dataset_id_fkey' ), nullable=True ),
    Column( "copied_from_library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id", use_alter=True, name='library_dataset_dataset_association_id_fkey' ), nullable=True ),
    Column( "name", TrimmedString( 255 ) ),
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

Library_table = Table( "library", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "root_folder_id", Integer, ForeignKey( "library_folder.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", String( 255 ), index=True ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ),
    Column( "description", TEXT ) )

LibraryFolder_table = Table( "library_folder", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "parent_id", Integer, ForeignKey( "library_folder.id" ), nullable = True, index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TEXT ),
    Column( "description", TEXT ),
    Column( "order_id", Integer ),
    Column( "item_count", Integer ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ),
    Column( "genome_build", TrimmedString( 40 ) ) )

LibraryItemInfoTemplateElement_table = Table( "library_item_info_template_element", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "optional", Boolean, index=True, default=True ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "name", TEXT ),
    Column( "description", TEXT ),
    Column( "type", TEXT, default='string' ),
    Column( "order_id", Integer ),
    Column( "options", JSONType() ),
    Column( "library_item_info_template_id", Integer, ForeignKey( "library_item_info_template.id" ) ) )
Index( "ix_liite_library_item_info_template_id", LibraryItemInfoTemplateElement_table.c.library_item_info_template_id )

LibraryItemInfoTemplate_table = Table( "library_item_info_template", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "optional", Boolean, index=True, default=True ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "name", TEXT ),
    Column( "description", TEXT ),
    Column( "item_count", Integer, default=0 ) )

LibraryInfoTemplateAssociation_table = Table( "library_info_template_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "library_id", Integer, ForeignKey( "library.id" ), nullable=True, index=True ),
    Column( "library_item_info_template_id", Integer, ForeignKey( "library_item_info_template.id" ) ) )
Index( "ix_lita_library_item_info_template_id", LibraryInfoTemplateAssociation_table.c.library_item_info_template_id )

LibraryFolderInfoTemplateAssociation_table = Table( "library_folder_info_template_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "library_folder_id", Integer, ForeignKey( "library_folder.id" ), nullable=True, index=True ),
    Column( "library_item_info_template_id", Integer, ForeignKey( "library_item_info_template.id" ) ) )
Index( "ix_lfita_library_item_info_template_id", LibraryFolderInfoTemplateAssociation_table.c.library_item_info_template_id )

LibraryDatasetInfoTemplateAssociation_table = Table( "library_dataset_info_template_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "library_dataset_id", Integer, ForeignKey( "library_dataset.id" ), nullable=True, index=True ),
    Column( "library_item_info_template_id", Integer, ForeignKey( "library_item_info_template.id" ) ) )
Index( "ix_ldita_library_item_info_template_id", LibraryDatasetInfoTemplateAssociation_table.c.library_item_info_template_id )

LibraryDatasetDatasetInfoTemplateAssociation_table = Table( "library_dataset_dataset_info_template_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), nullable=True ),
    Column( "library_item_info_template_id", Integer, ForeignKey( "library_item_info_template.id" ) ) )
Index( "ix_lddita_library_dataset_dataset_association_id", LibraryDatasetDatasetInfoTemplateAssociation_table.c.library_dataset_dataset_association_id )
Index( "ix_lddita_library_item_info_template_id", LibraryDatasetDatasetInfoTemplateAssociation_table.c.library_item_info_template_id )

LibraryItemInfoElement_table = Table( "library_item_info_element", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "contents", JSONType() ),
    Column( "library_item_info_id", Integer, ForeignKey( "library_item_info.id" ), index=True ),
    Column( "library_item_info_template_element_id", Integer, ForeignKey( "library_item_info_template_element.id" ) ) )
Index( "ix_liie_library_item_info_template_element_id", LibraryItemInfoElement_table.c.library_item_info_template_element_id )

LibraryItemInfo_table = Table( "library_item_info", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), nullable=True, index=True ),
    Column( "library_item_info_template_id", Integer, ForeignKey( "library_item_info_template.id" ), nullable=True, index=True ) )

LibraryInfoAssociation_table = Table( "library_info_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "library_id", Integer, ForeignKey( "library.id" ), nullable=True, index=True ),
    Column( "library_item_info_id", Integer, ForeignKey( "library_item_info.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), nullable=True, index=True ) )

LibraryFolderInfoAssociation_table = Table( "library_folder_info_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "library_folder_id", Integer, ForeignKey( "library_folder.id" ), nullable=True, index=True ),
    Column( "library_item_info_id", Integer, ForeignKey( "library_item_info.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), nullable=True, index=True ) )

LibraryDatasetInfoAssociation_table = Table( "library_dataset_info_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "library_dataset_id", Integer, ForeignKey( "library_dataset.id" ), nullable=True, index=True ),
    Column( "library_item_info_id", Integer, ForeignKey( "library_item_info.id" ), index=True ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), nullable=True, index=True ) )

LibraryDatasetDatasetInfoAssociation_table = Table( "library_dataset_dataset_info_association", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), nullable=True ),
    Column( "library_item_info_id", Integer, ForeignKey( "library_item_info.id" ) ),
    Column( "user_id", Integer, ForeignKey( "galaxy_user.id" ), nullable=True, index=True ) )
Index( "ix_lddia_library_dataset_dataset_association_id", LibraryDatasetDatasetInfoAssociation_table.c.library_dataset_dataset_association_id )
Index( "ix_lddia_library_item_info_id", LibraryDatasetDatasetInfoAssociation_table.c.library_item_info_id )

JobExternalOutputMetadata_table = Table( "job_external_output_metadata", metadata,
    Column( "id", Integer, primary_key=True ),
    Column( "job_id", Integer, ForeignKey( "job.id" ), index=True ),
    Column( "history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), index=True, nullable=True ),
    Column( "library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), nullable=True ),
    Column( "filename_in", String( 255 ) ),
    Column( "filename_out", String( 255 ) ),
    Column( "filename_results_code", String( 255 ) ),
    Column( "filename_kwds", String( 255 ) ),
    Column( "job_runner_external_pid", String( 255 ) ) )
Index( "ix_jeom_library_dataset_dataset_association_id", JobExternalOutputMetadata_table.c.library_dataset_dataset_association_id )

def upgrade(migrate_engine):
    db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )
    metadata.bind = migrate_engine
    # Load existing tables
    metadata.reflect()

    def nextval( table, col='id' ):
        if migrate_engine.name == 'postgres':
            return "nextval('%s_%s_seq')" % ( table, col )
        elif migrate_engine.name == 'mysql' or migrate_engine.name == 'sqlite':
            return "null"
        else:
            raise Exception( 'Unable to convert data for unknown database type: %s' % migrate_engine.name )

    def localtimestamp():
       if migrate_engine.name == 'postgres' or migrate_engine.name == 'mysql':
           return "LOCALTIMESTAMP"
       elif migrate_engine.name == 'sqlite':
           return "current_date || ' ' || current_time"
       else:
           raise Exception( 'Unable to convert data for unknown database type: %s' % db )

    def boolean_false():
       if migrate_engine.name == 'postgres' or migrate_engine.name == 'mysql':
           return False
       elif migrate_engine.name == 'sqlite':
           return 0
       else:
           raise Exception( 'Unable to convert data for unknown database type: %s' % db )

    # Add 2 new columns to the galaxy_user table
    try:
        User_table = Table( "galaxy_user", metadata, autoload=True )
    except NoSuchTableError:
        User_table = None
        log.debug( "Failed loading table galaxy_user" )
    if User_table is not None:
        try:
            col = Column( 'deleted', Boolean, index=True, default=False )
            col.create( User_table, index_name='ix_user_deleted')
            assert col is User_table.c.deleted
        except Exception, e:
            log.debug( "Adding column 'deleted' to galaxy_user table failed: %s" % ( str( e ) ) )
        try:
            col = Column( 'purged', Boolean, index=True, default=False )
            col.create( User_table, index_name='ix_user_purged')
            assert col is User_table.c.purged
        except Exception, e:
            log.debug( "Adding column 'purged' to galaxy_user table failed: %s" % ( str( e ) ) )
    # Add 1 new column to the history_dataset_association table
    try:
        HistoryDatasetAssociation_table = Table( "history_dataset_association", metadata, autoload=True )
    except NoSuchTableError:
        HistoryDatasetAssociation_table = None
        log.debug( "Failed loading table history_dataset_association" )
    if HistoryDatasetAssociation_table is not None:
        try:
            col = Column( 'copied_from_library_dataset_dataset_association_id', Integer, nullable=True )
            col.create( HistoryDatasetAssociation_table)
            assert col is HistoryDatasetAssociation_table.c.copied_from_library_dataset_dataset_association_id
        except Exception, e:
            log.debug( "Adding column 'copied_from_library_dataset_dataset_association_id' to history_dataset_association table failed: %s" % ( str( e ) ) )
    # Add 1 new column to the metadata_file table
    try:
        MetadataFile_table = Table( "metadata_file", metadata, autoload=True )
    except NoSuchTableError:
        MetadataFile_table = None
        log.debug( "Failed loading table metadata_file" )
    if MetadataFile_table is not None:
        try:
            col = Column( 'lda_id', Integer, index=True, nullable=True )
            col.create( MetadataFile_table, index_name='ix_metadata_file_lda_id')
            assert col is MetadataFile_table.c.lda_id
        except Exception, e:
            log.debug( "Adding column 'lda_id' to metadata_file table failed: %s" % ( str( e ) ) )
    # Add 1 new column to the stored_workflow table - changeset 2328
    try:
        StoredWorkflow_table = Table( "stored_workflow", metadata,
            Column( "latest_workflow_id", Integer,
                ForeignKey( "workflow.id", use_alter=True, name='stored_workflow_latest_workflow_id_fk' ), index=True ),
            autoload=True, extend_existing=True )
    except NoSuchTableError:
        StoredWorkflow_table = None
        log.debug( "Failed loading table stored_workflow" )
    if StoredWorkflow_table is not None:
        try:
            col = Column( 'importable', Boolean, default=False )
            col.create( StoredWorkflow_table )
            assert col is StoredWorkflow_table.c.importable
        except Exception, e:
            log.debug( "Adding column 'importable' to stored_workflow table failed: %s" % ( str( e ) ) )
    # Create an index on the Job.state column - changeset 2192
    try:
        Job_table = Table( "job", metadata, autoload=True )
    except NoSuchTableError:
        Job_table = None
        log.debug( "Failed loading table job" )
    if Job_table is not None:
        try:
            i = Index( 'ix_job_state', Job_table.c.state )
            i.create()
        except Exception, e:
            log.debug( "Adding index to job.state column failed: %s" % ( str( e ) ) )
    # Add all of the new tables above
    metadata.create_all()
    # Add 1 foreign key constraint to the history_dataset_association table
    try:
        HistoryDatasetAssociation_table = Table( "history_dataset_association", metadata, autoload=True )
    except NoSuchTableError:
        HistoryDatasetAssociation_table = None
        log.debug( "Failed loading table history_dataset_association" )
    try:
        LibraryDatasetDatasetAssociation_table = Table( "library_dataset_dataset_association", metadata, autoload=True )
    except NoSuchTableError:
        LibraryDatasetDatasetAssociation_table = None
        log.debug( "Failed loading table library_dataset_dataset_association" )
    if HistoryDatasetAssociation_table is not None and LibraryDatasetDatasetAssociation_table is not None:
        try:
            cons = ForeignKeyConstraint( [HistoryDatasetAssociation_table.c.copied_from_library_dataset_dataset_association_id],
                                         [LibraryDatasetDatasetAssociation_table.c.id],
                                         name='history_dataset_association_copied_from_library_dataset_da_fkey' )
            # Create the constraint
            cons.create()
        except Exception, e:
            log.debug( "Adding foreign key constraint 'history_dataset_association_copied_from_library_dataset_da_fkey' to table 'history_dataset_association' failed: %s" % ( str( e ) ) )
    # Add 1 foreign key constraint to the metadata_file table
    try:
        MetadataFile_table = Table( "metadata_file", metadata, autoload=True )
    except NoSuchTableError:
        MetadataFile_table = None
        log.debug( "Failed loading table metadata_file" )
    try:
        LibraryDatasetDatasetAssociation_table = Table( "library_dataset_dataset_association", metadata, autoload=True )
    except NoSuchTableError:
        LibraryDatasetDatasetAssociation_table = None
        log.debug( "Failed loading table library_dataset_dataset_association" )
    if migrate_engine.name != 'sqlite':
        #Sqlite can't alter table add foreign key.
        if MetadataFile_table is not None and LibraryDatasetDatasetAssociation_table is not None:
            try:
                cons = ForeignKeyConstraint( [MetadataFile_table.c.lda_id],
                                             [LibraryDatasetDatasetAssociation_table.c.id],
                                             name='metadata_file_lda_id_fkey' )
                # Create the constraint
                cons.create()
            except Exception, e:
                log.debug( "Adding foreign key constraint 'metadata_file_lda_id_fkey' to table 'metadata_file' failed: %s" % ( str( e ) ) )
    # Make sure we have at least 1 user
    cmd = "SELECT * FROM galaxy_user;"
    users = db_session.execute( cmd ).fetchall()
    if users:
        cmd = "SELECT * FROM role;"
        roles = db_session.execute( cmd ).fetchall()
        if not roles:
            # Create private roles for each user - pass 1
            cmd = \
                "INSERT INTO role " + \
                "SELECT %s AS id," + \
                "%s AS create_time," + \
                "%s AS update_time," + \
                "email AS name," + \
                "email AS description," + \
                "'private' As type," + \
                "%s AS deleted " + \
                "FROM galaxy_user " + \
                "ORDER BY id;"
            cmd = cmd % ( nextval('role'), localtimestamp(), localtimestamp(), boolean_false() )
            db_session.execute( cmd )
            # Create private roles for each user - pass 2
            if migrate_engine.name == 'postgres' or migrate_engine.name == 'sqlite':
                cmd = "UPDATE role SET description = 'Private role for ' || description;"
            elif migrate_engine.name == 'mysql':
                cmd = "UPDATE role SET description = CONCAT( 'Private role for ', description );"
            db_session.execute( cmd )
            # Create private roles for each user - pass 3
            cmd = \
                "INSERT INTO user_role_association " + \
                "SELECT %s AS id," + \
                "galaxy_user.id AS user_id," + \
                "role.id AS role_id," + \
                "%s AS create_time," + \
                "%s AS update_time " + \
                "FROM galaxy_user, role " + \
                "WHERE galaxy_user.email = role.name " + \
                "ORDER BY galaxy_user.id;"
            cmd = cmd % ( nextval('user_role_association'), localtimestamp(), localtimestamp() )
            db_session.execute( cmd )
            # Create default permissions for each user
            cmd = \
                "INSERT INTO default_user_permissions " + \
                "SELECT %s AS id," + \
                "galaxy_user.id AS user_id," + \
                "'manage permissions' AS action," + \
                "user_role_association.role_id AS role_id " + \
                "FROM galaxy_user " + \
                "JOIN user_role_association ON user_role_association.user_id = galaxy_user.id " + \
                "ORDER BY galaxy_user.id;"
            cmd = cmd % nextval('default_user_permissions')
            db_session.execute( cmd )
            # Create default history permissions for each active history associated with a user

            cmd = \
                "INSERT INTO default_history_permissions " + \
                "SELECT %s AS id," + \
                "history.id AS history_id," + \
                "'manage permissions' AS action," + \
                "user_role_association.role_id AS role_id " + \
                "FROM history " + \
                "JOIN user_role_association ON user_role_association.user_id = history.user_id " + \
                "WHERE history.purged = %s AND history.user_id IS NOT NULL;"
            cmd = cmd % ( nextval('default_history_permissions'), boolean_false() )
            db_session.execute( cmd )
            # Create "manage permissions" dataset_permissions for all activate-able datasets
            cmd = \
                "INSERT INTO dataset_permissions " + \
                "SELECT %s AS id," + \
                "%s AS create_time," + \
                "%s AS update_time," + \
                "'manage permissions' AS action," + \
                "history_dataset_association.dataset_id AS dataset_id," + \
                "user_role_association.role_id AS role_id " + \
                "FROM history " + \
                "JOIN history_dataset_association ON history_dataset_association.history_id = history.id " + \
                "JOIN dataset ON history_dataset_association.dataset_id = dataset.id " + \
                "JOIN user_role_association ON user_role_association.user_id = history.user_id " + \
                "WHERE dataset.purged = %s AND history.user_id IS NOT NULL;"
            cmd = cmd % ( nextval('dataset_permissions'), localtimestamp(), localtimestamp(), boolean_false() )
            db_session.execute( cmd )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    if migrate_engine.name == 'postgres':
        # http://blog.pythonisito.com/2008/01/cascading-drop-table-with-sqlalchemy.html
        from sqlalchemy.databases import postgres
        class PGCascadeSchemaDropper(postgres.PGSchemaDropper):
            def visit_table(self, table):
                for column in table.columns:
                    if column.default is not None:
                        self.traverse_single(column.default)
                self.append("\nDROP TABLE " +
                            self.preparer.format_table(table) +
                            " CASCADE")
                self.execute()
        postgres.dialect.schemadropper = PGCascadeSchemaDropper
    # Load existing tables
    metadata.reflect()
    # NOTE: all new data added in the upgrade method is eliminated here via table drops
    # Drop 1 foreign key constraint from the metadata_file table
    try:
        MetadataFile_table = Table( "metadata_file", metadata, autoload=True )
    except NoSuchTableError:
        MetadataFile_table = None
        log.debug( "Failed loading table metadata_file" )
    try:
        LibraryDatasetDatasetAssociation_table = Table( "library_dataset_dataset_association", metadata, autoload=True )
    except NoSuchTableError:
        LibraryDatasetDatasetAssociation_table = None
        log.debug( "Failed loading table library_dataset_dataset_association" )
    if MetadataFile_table is not None and LibraryDatasetDatasetAssociation_table is not None:
        try:
            cons = ForeignKeyConstraint( [MetadataFile_table.c.lda_id],
                                         [LibraryDatasetDatasetAssociation_table.c.id],
                                         name='metadata_file_lda_id_fkey' )
            # Drop the constraint
            cons.drop()
        except Exception, e:
            log.debug( "Dropping foreign key constraint 'metadata_file_lda_id_fkey' from table 'metadata_file' failed: %s" % ( str( e ) ) )
    # Drop 1 foreign key constraint from the history_dataset_association table
    try:
        HistoryDatasetAssociation_table = Table( "history_dataset_association", metadata, autoload=True )
    except NoSuchTableError:
        HistoryDatasetAssociation_table = None
        log.debug( "Failed loading table history_dataset_association" )
    try:
        LibraryDatasetDatasetAssociation_table = Table( "library_dataset_dataset_association", metadata, autoload=True )
    except NoSuchTableError:
        LibraryDatasetDatasetAssociation_table = None
        log.debug( "Failed loading table library_dataset_dataset_association" )
    if HistoryDatasetAssociation_table is not None and LibraryDatasetDatasetAssociation_table is not None:
        try:
            cons = ForeignKeyConstraint( [HistoryDatasetAssociation_table.c.copied_from_library_dataset_dataset_association_id],
                                         [LibraryDatasetDatasetAssociation_table.c.id],
                                         name='history_dataset_association_copied_from_library_dataset_da_fkey' )
            # Drop the constraint
            cons.drop()
        except Exception, e:
            log.debug( "Dropping foreign key constraint 'history_dataset_association_copied_from_library_dataset_da_fkey' from table 'history_dataset_association' failed: %s" % ( str( e ) ) )
    # Drop all of the new tables above
    try:
        UserGroupAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping user_group_association table failed: %s" % str( e ) )
    try:
        UserRoleAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping user_role_association table failed: %s" % str( e ) )
    try:
        GroupRoleAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping group_role_association table failed: %s" % str( e ) )
    try:
        Group_table.drop()
    except Exception, e:
        log.debug( "Dropping galaxy_group table failed: %s" % str( e ) )
    try:
        DatasetPermissions_table.drop()
    except Exception, e:
        log.debug( "Dropping dataset_permissions table failed: %s" % str( e ) )
    try:
        LibraryPermissions_table.drop()
    except Exception, e:
        log.debug( "Dropping library_permissions table failed: %s" % str( e ) )
    try:
        LibraryFolderPermissions_table.drop()
    except Exception, e:
        log.debug( "Dropping library_folder_permissions table failed: %s" % str( e ) )
    try:
        LibraryDatasetPermissions_table.drop()
    except Exception, e:
        log.debug( "Dropping library_dataset_permissions table failed: %s" % str( e ) )
    try:
        LibraryDatasetDatasetAssociationPermissions_table.drop()
    except Exception, e:
        log.debug( "Dropping library_dataset_dataset_association_permissions table failed: %s" % str( e ) )
    try:
        LibraryItemInfoPermissions_table.drop()
    except Exception, e:
        log.debug( "Dropping library_item_info_permissions table failed: %s" % str( e ) )
    try:
        LibraryItemInfoTemplatePermissions_table.drop()
    except Exception, e:
        log.debug( "Dropping library_item_info_template_permissions table failed: %s" % str( e ) )
    try:
        DefaultUserPermissions_table.drop()
    except Exception, e:
        log.debug( "Dropping default_user_permissions table failed: %s" % str( e ) )
    try:
        DefaultHistoryPermissions_table.drop()
    except Exception, e:
        log.debug( "Dropping default_history_permissions table failed: %s" % str( e ) )
    try:
        Role_table.drop()
    except Exception, e:
        log.debug( "Dropping role table failed: %s" % str( e ) )
    try:
        LibraryDatasetDatasetInfoAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping library_dataset_dataset_info_association table failed: %s" % str( e ) )
    try:
        LibraryDataset_table.drop()
    except Exception, e:
        log.debug( "Dropping library_dataset table failed: %s" % str( e ) )
    try:
        LibraryDatasetDatasetAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping library_dataset_dataset_association table failed: %s" % str( e ) )
    try:
        LibraryDatasetDatasetInfoTemplateAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping library_dataset_dataset_info_template_association table failed: %s" % str( e ) )
    try:
        JobExternalOutputMetadata_table.drop()
    except Exception, e:
        log.debug( "Dropping job_external_output_metadata table failed: %s" % str( e ) )
    try:
        Library_table.drop()
    except Exception, e:
        log.debug( "Dropping library table failed: %s" % str( e ) )
    try:
        LibraryFolder_table.drop()
    except Exception, e:
        log.debug( "Dropping library_folder table failed: %s" % str( e ) )
    try:
        LibraryItemInfoTemplateElement_table.drop()
    except Exception, e:
        log.debug( "Dropping library_item_info_template_element table failed: %s" % str( e ) )
    try:
        LibraryInfoTemplateAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping library_info_template_association table failed: %s" % str( e ) )
    try:
        LibraryFolderInfoTemplateAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping library_folder_info_template_association table failed: %s" % str( e ) )
    try:
        LibraryDatasetInfoTemplateAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping library_dataset_info_template_association table failed: %s" % str( e ) )
    try:
        LibraryInfoAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping library_info_association table failed: %s" % str( e ) )
    try:
        LibraryFolderInfoAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping library_folder_info_association table failed: %s" % str( e ) )
    try:
        LibraryDatasetInfoAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping library_dataset_info_association table failed: %s" % str( e ) )
    try:
        LibraryItemInfoElement_table.drop()
    except Exception, e:
        log.debug( "Dropping library_item_info_element table failed: %s" % str( e ) )
    try:
        LibraryItemInfo_table.drop()
    except Exception, e:
        log.debug( "Dropping library_item_info table failed: %s" % str( e ) )
    try:
        LibraryItemInfoTemplate_table.drop()
    except Exception, e:
        log.debug( "Dropping library_item_info_template table failed: %s" % str( e ) )
    # Drop the index on the Job.state column - changeset 2192
    try:
        Job_table = Table( "job", metadata, autoload=True )
    except NoSuchTableError:
        Job_table = None
        log.debug( "Failed loading table job" )
    if Job_table is not None:
        try:
            i = Index( 'ix_job_state', Job_table.c.state )
            i.drop()
        except Exception, e:
            log.debug( "Dropping index from job.state column failed: %s" % ( str( e ) ) )
    # Drop 1 column from the stored_workflow table - changeset 2328
    try:
        StoredWorkflow_table = Table( "stored_workflow", metadata, autoload=True )
    except NoSuchTableError:
        StoredWorkflow_table = None
        log.debug( "Failed loading table stored_workflow" )
    if StoredWorkflow_table is not None:
        try:
            col = StoredWorkflow_table.c.importable
            col.drop()
        except Exception, e:
            log.debug( "Dropping column 'importable' from stored_workflow table failed: %s" % ( str( e ) ) )
    # Drop 1 column from the metadata_file table
    try:
        MetadataFile_table = Table( "metadata_file", metadata, autoload=True )
    except NoSuchTableError:
        MetadataFile_table = None
        log.debug( "Failed loading table metadata_file" )
    if MetadataFile_table is not None:
        try:
            col = MetadataFile_table.c.lda_id
            col.drop()
        except Exception, e:
            log.debug( "Dropping column 'lda_id' from metadata_file table failed: %s" % ( str( e ) ) )
    # Drop 1 column from the history_dataset_association table
    try:
        HistoryDatasetAssociation_table = Table( "history_dataset_association", metadata, autoload=True )
    except NoSuchTableError:
        HistoryDatasetAssociation_table = None
        log.debug( "Failed loading table history_dataset_association" )
    if HistoryDatasetAssociation_table is not None:
        try:
            col = HistoryDatasetAssociation_table.c.copied_from_library_dataset_dataset_association_id
            col.drop()
        except Exception, e:
            log.debug( "Dropping column 'copied_from_library_dataset_dataset_association_id' from history_dataset_association table failed: %s" % ( str( e ) ) )
    # Drop 2 columns from the galaxy_user table
    try:
        User_table = Table( "galaxy_user", metadata, autoload=True )
    except NoSuchTableError:
        User_table = None
        log.debug( "Failed loading table galaxy_user" )
    if User_table is not None:
        try:
            col = User_table.c.deleted
            col.drop()
        except Exception, e:
            log.debug( "Dropping column 'deleted' from galaxy_user table failed: %s" % ( str( e ) ) )
        try:
            col = User_table.c.purged
            col.drop()
        except Exception, e:
            log.debug( "Dropping column 'purged' from galaxy_user table failed: %s" % ( str( e ) ) )
