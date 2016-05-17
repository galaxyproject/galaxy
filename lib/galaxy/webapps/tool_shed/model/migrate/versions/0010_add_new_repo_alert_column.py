"""
Migration script to add the new_repo_alert column to the galaxy_user table.
"""
import logging
import sys

from sqlalchemy import Boolean, Column, MetaData, Table

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
    # Create and initialize imported column in job table.
    User_table = Table( "galaxy_user", metadata, autoload=True )
    c = Column( "new_repo_alert", Boolean, default=False, index=True )
    try:
        # Create
        c.create( User_table, index_name="ix_galaxy_user_new_repo_alert")
        assert c is User_table.c.new_repo_alert
        # Initialize.
        if migrate_engine.name == 'mysql' or migrate_engine.name == 'sqlite':
            default_false = "0"
        elif migrate_engine.name in ['postgresql', 'postgres']:
            default_false = "false"
        else:
            log.debug("unknown migrate_engine dialect")
        migrate_engine.execute( "UPDATE galaxy_user SET new_repo_alert=%s" % default_false )
    except Exception as e:
        print "Adding new_repo_alert column to the galaxy_user table failed: %s" % str( e )
        log.debug( "Adding new_repo_alert column to the galaxy_user table failed: %s" % str( e ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    # Drop new_repo_alert column from galaxy_user table.
    User_table = Table( "galaxy_user", metadata, autoload=True )
    try:
        User_table.c.new_repo_alert.drop()
    except Exception as e:
        print "Dropping column new_repo_alert from the galaxy_user table failed: %s" % str( e )
        log.debug( "Dropping column new_repo_alert from the galaxy_user table failed: %s" % str( e ) )
