"""
Migration script to add 'ldda_parent_id' column to the implicitly_converted_dataset_association table.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

def upgrade():
    print __doc__
    metadata.reflect()
    try:
        Implicitly_converted_table = Table( "implicitly_converted_dataset_association", metadata, autoload=True )
        c = Column( "ldda_parent_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), index=True, nullable=True )
        c.create( Implicitly_converted_table )
        assert c is Implicitly_converted_table.c.ldda_parent_id
    except Exception, e:
        print "Adding ldda_parent_id column to implicitly_converted_dataset_association table failed: %s" % str( e )
        log.debug( "Adding ldda_parent_id column to implicitly_converted_dataset_association table failed: %s" % str( e ) )

def downgrade():
    metadata.reflect()
    try:
        Implicitly_converted_table = Table( "implicitly_converted_dataset_association", metadata, autoload=True )
        Implicitly_converted_table.c.ldda_parent_id.drop()
    except Exception, e:
        print "Dropping ldda_parent_id column from implicitly_converted_dataset_association table failed: %s" % str( e )
        log.debug( "Dropping ldda_parent_id column from implicitly_converted_dataset_association table failed: %s" % str( e ) )
