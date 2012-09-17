"""
Migration script to create missing indexes.  Adding new columns to existing tables via SQLAlchemy does not create the index, even if the column definition includes index=True.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *

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

indexes = (
    ( "ix_metadata_file_lda_id", 'metadata_file', 'lda_id' ),                   # 0003
    ( "ix_history_importable", 'history', 'importable' ),                       # 0007
    ( "ix_sample_bar_code", 'sample', 'bar_code' ),                             # 0009
    ( "ix_request_type_deleted", 'request_type', 'deleted' ),                   # 0012
    ( "ix_galaxy_user_username", 'galaxy_user', 'username' ),                   # 0014
    ( "ix_form_definition_type", 'form_definition', 'type' ),                   # 0019
    ( "ix_form_definition_layout", 'form_definition', 'layout' ),               # 0019
    ( "ix_job_library_folder_id", 'job', 'library_folder_id' ),                 # 0020
    ( "ix_galaxy_user_form_values_id", 'galaxy_user', 'form_values_id' ),       # 0025
    ( "ix_sample_library_id", 'sample', 'library_id' ),                         # 0037
    ( "ix_sample_folder_id", 'sample', 'folder_id' ),                           # 0037
    ( "ix_request_notification", 'request', 'notification' ),                   # 0057
    ( "ix_sd_external_service_id", 'sample_dataset', 'external_service_id' ),   # 0068
    ( "ix_job_handler", 'job', 'handler' ),                                     # 0094
    ( "ix_galaxy_user_email", 'galaxy_user', 'email' )                          # 0106
)

def upgrade():
    print __doc__
    metadata.reflect()

    # Create missing indexes
    for ix, table, col in indexes:
        try:
            log.debug("Creating index '%s' on column '%s' in table '%s'" % (ix, col, table))
            t = Table( table, metadata, autoload=True )
            Index( ix, t.c[col] ).create()
        except Exception, e:
            log.error("Unable to create index '%s': %s" % (ix, str(e)))

def downgrade():
    metadata.reflect()
    
    # Drop indexes
    for ix, table, col in indexes:
        try:
            t = Table( table, metadata, autoload=True )
            Index( ix, t.c[col] ).drop()
        except Exception, e:
            log.error("Unable to drop index '%s': %s" % (ix, str(e)))
