"""
Migration script to add the tool_test_errors, do_not_test, tools_functionally_correct, and time_last_tested columns to the repository_metadata table.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

import sys, logging
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()

def upgrade(migrate_engine):
    print __doc__
    metadata.bind = migrate_engine
    metadata.reflect()
    # Create and initialize tools_functionally_correct, do_not_test, time_last_tested, and tool_test_errors columns in repository_metadata table.
    RepositoryMetadata_table = Table( "repository_metadata", metadata, autoload=True )
    c = Column( "tools_functionally_correct", Boolean, default=False, index=True )
    try:
        # Create tools_functionally_correct column
        c.create( RepositoryMetadata_table, index_name="ix_repository_metadata_tfc" )
        assert c is RepositoryMetadata_table.c.tools_functionally_correct
        # Initialize.
        if migrate_engine.name == 'mysql' or migrate_engine.name == 'sqlite':
            default_false = "0"
        elif migrate_engine.name in ['postgresql', 'postgres']:
            default_false = "false"
        migrate_engine.execute( "UPDATE repository_metadata SET tools_functionally_correct=%s" % default_false )
    except Exception, e:
        print "Adding tools_functionally_correct column to the repository_metadata table failed: %s" % str( e )
        log.debug( "Adding tools_functionally_correct column to the repository_metadata table failed: %s" % str( e ) )
    c = Column( "do_not_test", Boolean, default=False, index=True )
    try:
        # Create do_not_test column
        c.create( RepositoryMetadata_table, index_name="ix_repository_metadata_dnt")
        assert c is RepositoryMetadata_table.c.do_not_test
        # Initialize.
        if migrate_engine.name == 'mysql' or migrate_engine.name == 'sqlite':
            default_false = "0"
        elif migrate_engine.name in ['postgresql', 'postgres']:
            default_false = "false"
        migrate_engine.execute( "UPDATE repository_metadata SET do_not_test=%s" % default_false )
    except Exception, e:
        print "Adding do_not_test column to the repository_metadata table failed: %s" % str( e )
        log.debug( "Adding do_not_test column to the repository_metadata table failed: %s" % str( e ) )
    c = Column( "time_last_tested", DateTime, default=None, nullable=True )
    try:
        # Create time_last_tested column
        c.create( RepositoryMetadata_table, index_name="ix_repository_metadata_tlt")
        assert c is RepositoryMetadata_table.c.time_last_tested
    except Exception, e:
        print "Adding time_last_tested column to the repository_metadata table failed: %s" % str( e )
        log.debug( "Adding time_last_tested column to the repository_metadata table failed: %s" % str( e ) )
    c = Column( "tool_test_errors", JSONType, nullable=True )
    try:
        # Create tool_test_errors column
        c.create( RepositoryMetadata_table, index_name="ix_repository_metadata_tte")
        assert c is RepositoryMetadata_table.c.tool_test_errors
    except Exception, e:
        print "Adding tool_test_errors column to the repository_metadata table failed: %s" % str( e )
        log.debug( "Adding tool_test_errors column to the repository_metadata table failed: %s" % str( e ) )

def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    # Drop tool_test_errors, time_last_tested, do_not_test, and tools_functionally_correct columns from repository_metadata table.
    RepositoryMetadata_table = Table( "repository_metadata", metadata, autoload=True )
    try:
        RepositoryMetadata_table.c.tool_test_errors.drop()
    except Exception, e:
        print "Dropping column tool_test_errors from the repository_metadata table failed: %s" % str( e )
        log.debug( "Dropping column tool_test_errors from the repository_metadata table failed: %s" % str( e ) )
    try:
        RepositoryMetadata_table.c.time_last_tested.drop()
    except Exception, e:
        print "Dropping column time_last_tested from the repository_metadata table failed: %s" % str( e )
        log.debug( "Dropping column time_last_tested from the repository_metadata table failed: %s" % str( e ) )
    try:
        RepositoryMetadata_table.c.do_not_test.drop()
    except Exception, e:
        print "Dropping column do_not_test from the repository_metadata table failed: %s" % str( e )
        log.debug( "Dropping column do_not_test from the repository_metadata table failed: %s" % str( e ) )
    try:
        RepositoryMetadata_table.c.tools_functionally_correct.drop()
    except Exception, e:
        print "Dropping column tools_functionally_correct from the repository_metadata table failed: %s" % str( e )
        log.debug( "Dropping column tools_functionally_correct from the repository_metadata table failed: %s" % str( e ) )
