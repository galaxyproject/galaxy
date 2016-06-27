"""
This script adds a foreign key to the form_values table in the galaxy_user table
"""
from __future__ import print_function

import datetime
import logging
import sys

from migrate import ForeignKeyConstraint
from sqlalchemy import Column, Integer, MetaData, Table
from sqlalchemy.exc import NoSuchTableError

now = datetime.datetime.utcnow
log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData()


def display_migration_details():
    print("========================================")
    print("This script adds a foreign key to the form_values table in the galaxy_user table")
    print("========================================")


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    display_migration_details()
    # Load existing tables
    metadata.reflect()
    try:
        User_table = Table( "galaxy_user", metadata, autoload=True )
    except NoSuchTableError:
        User_table = None
        log.debug( "Failed loading table galaxy_user" )
    if User_table is not None:
        try:
            col = Column( "form_values_id", Integer, index=True )
            col.create( User_table, index_name='ix_user_form_values_id')
            assert col is User_table.c.form_values_id
        except Exception as e:
            log.debug( "Adding column 'form_values_id' to galaxy_user table failed: %s" % ( str( e ) ) )
        try:
            FormValues_table = Table( "form_values", metadata, autoload=True )
        except NoSuchTableError:
            FormValues_table = None
            log.debug( "Failed loading table form_values" )
        if migrate_engine.name != 'sqlite':
            # Add 1 foreign key constraint to the form_values table
            if User_table is not None and FormValues_table is not None:
                try:
                    cons = ForeignKeyConstraint( [User_table.c.form_values_id],
                                                 [FormValues_table.c.id],
                                                 name='user_form_values_id_fk' )
                    # Create the constraint
                    cons.create()
                except Exception as e:
                    log.debug( "Adding foreign key constraint 'user_form_values_id_fk' to table 'galaxy_user' failed: %s" % ( str( e ) ) )


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    pass
