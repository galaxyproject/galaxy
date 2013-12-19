import logging
import os
import sys

cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.append( cwd )

new_path = [ os.path.join( cwd, "lib" ) ]
if new_path not in sys.path:
    new_path.extend( sys.path )
    sys.path = new_path

from galaxy import eggs

eggs.require( 'mercurial' )

from mercurial import hg
from mercurial import ui

log = logging.getLogger(__name__)

def get_database_version( app ):
    '''
    This method returns the value of the version column from the migrate_version table, using the provided app's SQLAlchemy session to determine
    which table to get that from. This way, it's provided with an instance of a Galaxy UniverseApplication, it will return the Galaxy instance's
    database migration version. If a tool shed UniverseApplication is provided, it returns the tool shed's database migration version.
    '''
    sa_session = app.model.context.current
    result = sa_session.execute( 'SELECT version FROM migrate_version LIMIT 1' )
    # This query will return the following structure:
    # row = [ column 0, column 1, ..., column n ]
    # rows = [ row 0, row 1, ..., row n ]
    # The first column in the first row is the version number we want.
    for row in result:
        version = row[ 0 ]
        break
    return version

def get_repository_current_revision( repo_path ):
    '''
    This method uses the python mercurial API to get the current working directory's mercurial changeset hash. Note that if the author of mercurial
    changes the API, this method will have to be updated or replaced.
    '''
    # Initialize a mercurial repo object from the provided path.
    repo = hg.repository( ui.ui(), repo_path )
    # Get the working directory's change context.
    ctx = repo[ None ]
    # Extract the changeset hash of the first parent of that change context (the most recent changeset to which the working directory was updated).
    changectx = ctx.parents()[ 0 ]
    # Also get the numeric revision, so we can return the customary id:hash changeset identifiers.
    ctx_rev = changectx.rev()
    hg_id = '%d:%s' % ( ctx_rev, str( changectx ) )
    return hg_id
