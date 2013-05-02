"""
This migration script eliminates all of the tables that were used for the 1st version of the
library templates where template fields and contents were each stored as a separate table row
in various library item tables.  All of these tables are dropped in this script, eliminating all
existing template data.  A total of 14 existing tables are dropped.

We're now basing library templates on forms, so field contents are
stored as a jsonified list in the form_values table.  This script introduces the following 3
new association tables:
1) library_info_association
2) library_folder_info_association
3) library_dataset_dataset_info_association

If using mysql, this script will throw an (OperationalError) exception due to a long index name on
the library_dataset_dataset_info_association table, which is OK because the script creates an index
with a shortened name.
"""
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import *
from migrate import *
from migrate.changeset import *
import sys, logging

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()

def display_migration_details():
    print "========================================"
    print "This migration script eliminates all of the tables that were used for the 1st version of the"
    print "library templates where template fields and contents were each stored as a separate table row"
    print "in various library item tables.  All of these tables are dropped in this script, eliminating all"
    print "existing template data.  A total of 14 existing tables are dropped."
    print ""
    print "We're now basing library templates on Galaxy forms, so field contents are stored as a jsonified"
    print "list in the form_values table.  This script introduces the following 3 new association tables:"
    print "1) library_info_association"
    print "2) library_folder_info_association"
    print "3) library_dataset_dataset_info_association"
    print ""
    print "If using mysql, this script will throw an (OperationalError) exception due to a long index name"
    print "on the library_dataset_dataset_info_association table, which is OK because the script creates"
    print "an index with a shortened name."
    print "========================================"

LibraryInfoAssociation_table = Table( 'library_info_association', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "library_id", Integer, ForeignKey( "library.id" ), index=True ),
    Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ) )

LibraryFolderInfoAssociation_table = Table( 'library_folder_info_association', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "library_folder_id", Integer, ForeignKey( "library_folder.id" ), nullable=True, index=True ),
    Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ) )

LibraryDatasetDatasetInfoAssociation_table = Table( 'library_dataset_dataset_info_association', metadata,
    Column( "id", Integer, primary_key=True),
    Column( "library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), nullable=True, index=True ),
    Column( "form_definition_id", Integer, ForeignKey( "form_definition.id" ), index=True ),
    Column( "form_values_id", Integer, ForeignKey( "form_values.id" ), index=True ) )

def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    display_migration_details()
    # Load existing tables
    metadata.reflect()
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
    # Drop all of the original library_item_info tables
    # NOTE: all existing library item into template data is eliminated here via table drops
    try:
        LibraryItemInfoPermissions_table = Table( "library_item_info_permissions", metadata, autoload=True )
    except NoSuchTableError:
        LibraryItemInfoPermissions_table = None
        log.debug( "Failed loading table library_item_info_permissions" )
    try:
        LibraryItemInfoPermissions_table.drop()
    except Exception, e:
        log.debug( "Dropping library_item_info_permissions table failed: %s" % str( e ) )

    try:
        LibraryItemInfoTemplatePermissions_table = Table( "library_item_info_template_permissions", metadata, autoload=True )
    except NoSuchTableError:
        LibraryItemInfoTemplatePermissions_table = None
        log.debug( "Failed loading table library_item_info_template_permissions" )
    try:
        LibraryItemInfoTemplatePermissions_table.drop()
    except Exception, e:
        log.debug( "Dropping library_item_info_template_permissions table failed: %s" % str( e ) )

    try:
        LibraryItemInfoElement_table = Table( "library_item_info_element", metadata, autoload=True )
    except NoSuchTableError:
        LibraryItemInfoElement_table = None
        log.debug( "Failed loading table library_item_info_element" )
    try:
        LibraryItemInfoElement_table.drop()
    except Exception, e:
        log.debug( "Dropping library_item_info_element table failed: %s" % str( e ) )

    try:
        LibraryItemInfoTemplateElement_table = Table( "library_item_info_template_element", metadata, autoload=True )
    except NoSuchTableError:
        LibraryItemInfoTemplateElement_table = None
        log.debug( "Failed loading table library_item_info_template_element" )
    try:
        LibraryItemInfoTemplateElement_table.drop()
    except Exception, e:
        log.debug( "Dropping library_item_info_template_element table failed: %s" % str( e ) )

    try:
        LibraryInfoTemplateAssociation_table = Table( "library_info_template_association", metadata, autoload=True )
    except NoSuchTableError:
        LibraryInfoTemplateAssociation_table = None
        log.debug( "Failed loading table library_info_template_association" )
    try:
        LibraryInfoTemplateAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping library_info_template_association table failed: %s" % str( e ) )

    try:
        LibraryFolderInfoTemplateAssociation_table = Table( "library_folder_info_template_association", metadata, autoload=True )
    except NoSuchTableError:
        LibraryFolderInfoTemplateAssociation_table = None
        log.debug( "Failed loading table library_folder_info_template_association" )
    try:
        LibraryFolderInfoTemplateAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping library_folder_info_template_association table failed: %s" % str( e ) )

    try:
        LibraryDatasetInfoTemplateAssociation_table = Table( "library_dataset_info_template_association", metadata, autoload=True )
    except NoSuchTableError:
        LibraryDatasetInfoTemplateAssociation_table = None
        log.debug( "Failed loading table library_dataset_info_template_association" )
    try:
        LibraryDatasetInfoTemplateAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping library_dataset_info_template_association table failed: %s" % str( e ) )

    try:
        LibraryDatasetDatasetInfoTemplateAssociation_table = Table( "library_dataset_dataset_info_template_association", metadata, autoload=True )
    except NoSuchTableError:
        LibraryDatasetDatasetInfoTemplateAssociation_table = None
        log.debug( "Failed loading table library_dataset_dataset_info_template_association" )
    try:
        LibraryDatasetDatasetInfoTemplateAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping library_dataset_dataset_info_template_association table failed: %s" % str( e ) )

    try:
        LibraryInfoAssociation_table = Table( "library_info_association", metadata, autoload=True )
    except NoSuchTableError:
        LibraryInfoAssociation_table = None
        log.debug( "Failed loading table library_info_association" )
    try:
        LibraryInfoAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping library_info_association table failed: %s" % str( e ) )

    try:
        LibraryFolderInfoAssociation_table = Table( "library_folder_info_association", metadata, autoload=True )
    except NoSuchTableError:
        LibraryFolderInfoAssociation_table = None
        log.debug( "Failed loading table library_folder_info_association" )
    try:
        LibraryFolderInfoAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping library_folder_info_association table failed: %s" % str( e ) )

    try:
        LibraryDatasetInfoAssociation_table = Table( "library_dataset_info_association", metadata, autoload=True )
    except NoSuchTableError:
        LibraryDatasetInfoAssociation_table = None
        log.debug( "Failed loading table library_dataset_info_association" )
    try:
        LibraryDatasetInfoAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping library_dataset_info_association table failed: %s" % str( e ) )

    try:
        LibraryDatasetDatasetInfoAssociation_table = Table( "library_dataset_dataset_info_association", metadata, autoload=True )
    except NoSuchTableError:
        LibraryDatasetDatasetInfoAssociation_table = None
        log.debug( "Failed loading table library_dataset_dataset_info_association" )
    try:
        LibraryDatasetDatasetInfoAssociation_table.drop()
    except Exception, e:
        log.debug( "Dropping library_dataset_dataset_info_association table failed: %s" % str( e ) )

    try:
        LibraryItemInfo_table = Table( "library_item_info", metadata, autoload=True )
    except NoSuchTableError:
        LibraryItemInfo_table = None
        log.debug( "Failed loading table library_item_info" )
    try:
        LibraryItemInfo_table.drop()
    except Exception, e:
        log.debug( "Dropping library_item_info table failed: %s" % str( e ) )

    try:
        LibraryItemInfoTemplate_table = Table( "library_item_info_template", metadata, autoload=True )
    except NoSuchTableError:
        LibraryItemInfoTemplate_table = None
        log.debug( "Failed loading table library_item_info_template" )
    try:
        LibraryItemInfoTemplate_table.drop()
    except Exception, e:
        log.debug( "Dropping library_item_info_template table failed: %s" % str( e ) )

    # Create all new tables above
    try:
        LibraryInfoAssociation_table.create()
    except Exception, e:
        log.debug( "Creating library_info_association table failed: %s" % str( e ) )
    try:
        LibraryFolderInfoAssociation_table.create()
    except Exception, e:
        log.debug( "Creating library_folder_info_association table failed: %s" % str( e ) )
    try:
        LibraryDatasetDatasetInfoAssociation_table.create()
    except Exception, e:
        log.debug( "Creating library_dataset_dataset_info_association table failed: %s" % str( e ) )
    # Fix index on LibraryDatasetDatasetInfoAssociation_table for mysql
    if migrate_engine.name == 'mysql':
        # Load existing tables
        metadata.reflect()
        i = Index( "ix_lddaia_ldda_id", LibraryDatasetDatasetInfoAssociation_table.c.library_dataset_dataset_association_id )
        try:
            i.create()
        except Exception, e:
            log.debug( "Adding index 'ix_lddaia_ldda_id' to table 'library_dataset_dataset_info_association' table failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    log.debug( "Downgrade is not possible." )
