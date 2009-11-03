"""
This script adds a foreign key to the form_values table in the galaxy_user table
"""
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exceptions import *
from migrate import *
from migrate.changeset import *
import datetime
now = datetime.datetime.utcnow
import sys, logging
# Need our custom types, but don't import anything else from model
from galaxy.model.custom_types import *

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

def display_migration_details():
    print "========================================"
    print "This script adds a foreign key to the form_values table in the galaxy_user table"
    print "========================================"
def upgrade():
    display_migration_details()
    # Load existing tables
    metadata.reflect()
    try:
        User_table = Table( "galaxy_user", metadata, autoload=True )
    except NoSuchTableError:
        User_table = None
        log.debug( "Failed loading table galaxy_user" )
    if User_table:
        try:
            col = Column( "form_values_id", Integer, index=True )
            col.create( User_table )
            assert col is User_table.c.form_values_id
        except Exception, e:
            log.debug( "Adding column 'form_values_id' to galaxy_user table failed: %s" % ( str( e ) ) )
        try:
            FormValues_table = Table( "form_values", metadata, autoload=True )
        except NoSuchTableError:
            FormValues_table = None
            log.debug( "Failed loading table form_values" )
        # Add 1 foreign key constraint to the form_values table
        if User_table and FormValues_table:
            try:
                cons = ForeignKeyConstraint( [User_table.c.form_values_id],
                                             [FormValues_table.c.id],
                                             name='user_form_values_id_fk' )
                # Create the constraint
                cons.create()
            except Exception, e:
                log.debug( "Adding foreign key constraint 'user_form_values_id_fk' to table 'galaxy_user' failed: %s" % ( str( e ) ) )
def downgrade():
    pass
