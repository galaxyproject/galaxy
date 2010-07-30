"""
Migration script to add the sample_dataset table and remove the 'dataset_files' column 
from the 'sample' table
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


def nextval( table, col='id' ):
    if migrate_engine.name == 'postgres':
        return "nextval('%s_%s_seq')" % ( table, col )
    elif migrate_engine.name == 'mysql' or migrate_engine.name == 'sqlite':
        return "null"
    else:
        raise Exception( 'Unable to convert data for unknown database type: %s' % migrate_engine.name )
    
def localtimestamp():
   if migrate_engine.name == 'postgres' or migrate_engine.name == 'mysql':
       return "LOCALTIMESTAMP"
   elif migrate_engine.name == 'sqlite':
       return "current_date || ' ' || current_time"
   else:
       raise Exception( 'Unable to convert data for unknown database type: %s' % db )

SampleDataset_table = Table('sample_dataset', metadata,
                            Column( "id", Integer, primary_key=True ),
                            Column( "create_time", DateTime, default=now ),
                            Column( "update_time", DateTime, default=now, onupdate=now ),
                            Column( "sample_id", Integer, ForeignKey( "sample.id" ), index=True ), 
                            Column( "name", TrimmedString( 255 ), nullable=False ),
                            Column( "file_path", TrimmedString( 255 ), nullable=False ),
                            Column( "status", TrimmedString( 255 ), nullable=False ),
                            Column( "error_msg", TEXT ),
                            Column( "size", TrimmedString( 255 ) ) )

def upgrade():
    print __doc__
    metadata.reflect()
    try:
        SampleDataset_table.create()
    except Exception, e:
        log.debug( "Creating sample_dataset table failed: %s" % str( e ) )
        
    cmd = "SELECT id, dataset_files FROM sample"
    result = db_session.execute( cmd )
    for r in result:
        sample_id = r[0]
        if r[1]:
            dataset_files = from_json_string(r[1])
            for df in dataset_files:
                if type(df) == type(dict()):
                    cmd = "INSERT INTO sample_dataset VALUES (%s, %s, %s, %s, '%s', '%s', '%s', '%s', '%s')"
                    cmd = cmd % ( nextval('sample_dataset'),
                                  localtimestamp(),
                                  localtimestamp(),
                                  str(sample_id),
                                  df.get('name', ''),
                                  df.get('filepath', ''),
                                  df.get('status', '').replace('"', '').replace("'", ""),
                                  "",
                                  df.get('size', '').replace('"', '').replace("'", "").replace(df.get('filepath', ''), '').strip() )
                db_session.execute( cmd )
            
    # Delete the dataset_files column in the Sample table
    try:
        Sample_table = Table( "sample", metadata, autoload=True )
    except NoSuchTableError:
        Sample_table = None
        log.debug( "Failed loading table sample" )
    if Sample_table:
        try:
            Sample_table.c.dataset_files.drop()
        except Exception, e:
            log.debug( "Deleting column 'dataset_files' from the 'sample' table failed: %s" % ( str( e ) ) )   


def downgrade():
    pass