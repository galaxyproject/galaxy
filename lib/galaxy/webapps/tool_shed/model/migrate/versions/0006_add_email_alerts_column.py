"""
Migration script to add the email_alerts column to the repository table.
"""
import logging
import sys

from sqlalchemy import Column, MetaData, Table

# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import JSONType

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
    Repository_table = Table( "repository", metadata, autoload=True )
    c = Column( "email_alerts", JSONType, nullable=True )
    try:
        # Create
        c.create( Repository_table )
        assert c is Repository_table.c.email_alerts
    except Exception as e:
        print "Adding email_alerts column to the repository table failed: %s" % str( e )
        log.debug( "Adding email_alerts column to the repository table failed: %s" % str( e ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    # Drop email_alerts column from repository table.
    Repository_table = Table( "repository", metadata, autoload=True )
    try:
        Repository_table.c.email_alerts.drop()
    except Exception as e:
        print "Dropping column email_alerts from the repository table failed: %s" % str( e )
        log.debug( "Dropping column email_alerts from the repository table failed: %s" % str( e ) )
