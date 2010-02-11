"""
Migration script to add an inheritable column to the following tables:
library_info_association, library_folder_info_association.
"""

from sqlalchemy import *
from migrate import *
from migrate.changeset import *

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )

def upgrade():
    print __doc__
    metadata.reflect()
    
    LibraryInfoAssociation_table = Table( "library_info_association", metadata, autoload=True )
    c = Column( "inheritable", Boolean, index=True, default=False )
    c.create( LibraryInfoAssociation_table )
    assert c is LibraryInfoAssociation_table.c.inheritable
    cmd = "UPDATE library_info_association SET inheritable = false"
    try:
        db_session.execute( cmd )
    except Exception, e:
        log.debug( "Setting value of column inheritable to false in library_info_association failed: %s" % ( str( e ) ) )
    
    LibraryFolderInfoAssociation_table = Table( "library_folder_info_association", metadata, autoload=True )
    c = Column( "inheritable", Boolean, index=True, default=False )
    c.create( LibraryFolderInfoAssociation_table )
    assert c is LibraryFolderInfoAssociation_table.c.inheritable
    cmd = "UPDATE library_folder_info_association SET inheritable = false"
    try:
        db_session.execute( cmd )
    except Exception, e:
        log.debug( "Setting value of column inheritable to false in library_folder_info_association failed: %s" % ( str( e ) ) )

def downgrade():
    pass
