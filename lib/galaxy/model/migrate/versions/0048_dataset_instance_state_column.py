"""
Add a state column to the history_dataset_association and library_dataset_dataset_association table.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import *
from migrate import *
from migrate.changeset import *
from galaxy.model.custom_types import *

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

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

DATASET_INSTANCE_TABLE_NAMES = [ 'history_dataset_association', 'library_dataset_dataset_association' ]

def upgrade():
    print __doc__
    metadata.reflect()
    dataset_instance_tables = []
    for table_name in DATASET_INSTANCE_TABLE_NAMES:
        try:
            dataset_instance_tables.append( ( table_name, Table( table_name, metadata, autoload=True ) ) )
        except NoSuchTableError:
            log.debug( "Failed loading table %s" % table_name )
    if dataset_instance_tables:
        for table_name, dataset_instance_table in dataset_instance_tables:
            try:
                col = Column( "state", TrimmedString( 64 ), index=True, nullable=True )
                col.create( dataset_instance_table )
                assert col is dataset_instance_table.c.state
            except Exception, e:
                log.debug( "Adding column 'state' to %s table failed: %s" % ( table_name, str( e ) ) )
            try:
                i = Index( "ix_%s_state" % table_name, dataset_instance_table.c.state )
                i.create()
            except Exception, e:
                log.debug( "Adding index 'ix_%s_state' failed: %s" % ( table_name, str( e ) ) )
def downgrade():
    metadata.reflect()
    dataset_instance_tables = []
    for table_name in DATASET_INSTANCE_TABLE_NAMES:
        try:
            dataset_instance_tables.append( ( table_name, Table( table_name, metadata, autoload=True ) ) )
        except NoSuchTableError:
            log.debug( "Failed loading table %s" % table_name )
    if dataset_instance_tables:
        for table_name, dataset_instance_table in dataset_instance_tables:
            try:
                col = dataset_instance_table.c.state
                col.drop()
            except Exception, e:
                log.debug( "Dropping column 'state' from %s table failed: %s" % ( table_name, str( e ) ) )
