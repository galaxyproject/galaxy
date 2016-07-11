"""
Add a state column to the history_dataset_association and library_dataset_dataset_association table.
"""
from __future__ import print_function

import datetime
import logging
import sys

from sqlalchemy import Column, MetaData, Table
from sqlalchemy.exc import NoSuchTableError

from galaxy.model.custom_types import TrimmedString

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()

DATASET_INSTANCE_TABLE_NAMES = [ 'history_dataset_association', 'library_dataset_dataset_association' ]


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    print(__doc__)
    metadata.reflect()
    dataset_instance_tables = []
    for table_name in DATASET_INSTANCE_TABLE_NAMES:
        try:
            dataset_instance_tables.append( ( table_name, Table( table_name, metadata, autoload=True ) ) )
        except NoSuchTableError:
            log.debug( "Failed loading table %s" % table_name )
    if dataset_instance_tables:
        for table_name, dataset_instance_table in dataset_instance_tables:
            index_name = "ix_%s_state" % table_name
            try:
                col = Column( "state", TrimmedString( 64 ), index=True, nullable=True )
                col.create( dataset_instance_table, index_name=index_name)
                assert col is dataset_instance_table.c.state
            except Exception as e:
                log.debug( "Adding column 'state' to %s table failed: %s" % ( table_name, str( e ) ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
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
            except Exception as e:
                log.debug( "Dropping column 'state' from %s table failed: %s" % ( table_name, str( e ) ) )
