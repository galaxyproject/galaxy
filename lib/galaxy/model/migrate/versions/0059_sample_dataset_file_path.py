"""
Migration script to modify the 'file_path' field type in 'sample_dataset' table 
to 'TEXT' so that it can support large file paths exceeding 255 characters
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
from sqlalchemy.exc import *

from galaxy.model.custom_types import *
from galaxy.util.json import from_json_string, to_json_string

import datetime
now = datetime.datetime.utcnow

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )


def upgrade():
    print __doc__
    metadata.reflect()
    try:
        SampleDataset_table = Table( "sample_dataset", metadata, autoload=True )
    except NoSuchTableError, e:
        SampleDataset_table = None
        log.debug( "Failed loading table 'sample_dataset'" )

    if SampleDataset_table:
        cmd = "SELECT id, file_path FROM sample_dataset"
        result = db_session.execute( cmd )
        filepath_dict = {}
        for r in result:
            id = int(r[0])
            filepath_dict[id] = r[1]
        # remove the 'file_path' column
        try:
            SampleDataset_table.c.file_path.drop()
        except Exception, e:
            log.debug( "Deleting column 'file_path' from the 'sample_dataset' table failed: %s" % ( str( e ) ) )   
        # create the column again
        try:
            col = Column( "file_path", TEXT )
            col.create( SampleDataset_table )
            assert col is SampleDataset_table.c.file_path
        except Exception, e:
            log.debug( "Creating column 'file_path' in the 'sample_dataset' table failed: %s" % ( str( e ) ) )   

        for id, file_path in filepath_dict.items():
            cmd = "update sample_dataset set file_path='%s' where id=%i" % (file_path, id)
            db_session.execute( cmd )            

def downgrade():
    pass