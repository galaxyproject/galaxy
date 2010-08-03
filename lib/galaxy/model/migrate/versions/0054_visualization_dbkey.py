"""
Migration script to add dbkey column for visualization.
"""

from sqlalchemy import *
from sqlalchemy.orm import *
from migrate import *
from migrate.changeset import *
from galaxy.util.json import from_json_string

import logging
log = logging.getLogger( __name__ )

metadata = MetaData( migrate_engine )
db_session = scoped_session( sessionmaker( bind=migrate_engine, autoflush=False, autocommit=True ) )

def upgrade():
    
    print __doc__
    metadata.reflect()
    
    Visualization_table = Table( "visualization", metadata, autoload=True )
    Visualization_revision_table = Table( "visualization_revision", metadata, autoload=True )

    # Create dbkey columns.
    x = Column( "dbkey", TEXT, index=True )
    y = Column( "dbkey", TEXT, index=True )
    x.create( Visualization_table )
    y.create( Visualization_revision_table )
    assert x is Visualization_table.c.dbkey
    assert y is Visualization_revision_table.c.dbkey
    
    try:
        i = Index( "ix_visualization_dbkey", Visualization_table.c.dbkey )
        i.create()
    except:
        pass
    
    try:
        i = Index( "ix_visualization_revision_dbkey", Visualization_revision_table.c.dbkey )
        i.create()
    except:
        pass
    
    all_viz = db_session.execute( "SELECT visualization.id as viz_id, visualization_revision.id as viz_rev_id, visualization_revision.config FROM visualization_revision \
                    LEFT JOIN visualization ON visualization.id=visualization_revision.visualization_id" )
    for viz in all_viz:
        viz_id = viz['viz_id']
        viz_rev_id = viz['viz_rev_id']
        if viz[Visualization_revision_table.c.config]:
            dbkey = from_json_string(viz[Visualization_revision_table.c.config]).get('dbkey', "").replace("'", "\\'")
            db_session.execute("UPDATE visualization_revision SET dbkey='%s' WHERE id=%s" % (dbkey, viz_rev_id))
            db_session.execute("UPDATE visualization SET dbkey='%s' WHERE id=%s" % (dbkey, viz_id))

def downgrade():
    metadata.reflect()
    
    Visualization_table = Table( "visualization", metadata, autoload=True )
    Visualization_revision_table = Table( "visualization_revision", metadata, autoload=True )

    Visualization_table.c.dbkey.drop()
    Visualization_revision_table.c.dbkey.drop()
