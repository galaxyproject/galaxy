import os, tarfile, tempfile, shutil
from galaxy.web.base.controller import *
from galaxy.webapps.community import model
from galaxy.model.orm import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.web.form_builder import SelectField
from galaxy.model.item_attrs import UsesItemRatings
from mercurial import hg, ui
import logging
log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

class ItemRatings( UsesItemRatings ):
    """Overrides rate_item method since we also allow for comments"""
    def rate_item( self, trans, user, item, rating, comment='' ):
        """ Rate an item. Return type is <item_class>RatingAssociation. """
        item_rating = self.get_user_item_rating( trans.sa_session, user, item, webapp_model=trans.model )
        if not item_rating:
            # User has not yet rated item; create rating.
            item_rating_assoc_class = self._get_item_rating_assoc_class( item, webapp_model=trans.model )
            item_rating = item_rating_assoc_class()
            item_rating.user = trans.user
            item_rating.set_item( item )
            item_rating.rating = rating
            item_rating.comment = comment
            trans.sa_session.add( item_rating )
            trans.sa_session.flush()
        elif item_rating.rating != rating or item_rating.comment != comment:
            # User has previously rated item; update rating.
            item_rating.rating = rating
            item_rating.comment = comment
            trans.sa_session.add( item_rating )
            trans.sa_session.flush()
        return item_rating

## ---- Utility methods -------------------------------------------------------

def get_categories( trans ):
    """Get all categories from the database"""
    return trans.sa_session.query( trans.model.Category ) \
                           .filter( trans.model.Category.table.c.deleted==False ) \
                           .order_by( trans.model.Category.table.c.name ).all()
def get_category( trans, id ):
    """Get a category from the database"""
    return trans.sa_session.query( trans.model.Category ).get( trans.security.decode_id( id ) )
def get_repository( trans, id ):
    """Get a repository from the database via id"""
    return trans.sa_session.query( trans.model.Repository ).get( trans.security.decode_id( id ) )
def get_repository_by_name( trans, name ):
    """Get a repository from the database via name"""
    return trans.sa_session.query( app.model.Repository ).filter_by( name=name ).one()
def get_repository_tip( repository ):
    # The received repository must be a mercurial repository, not a db record.
    tip_changeset = repository.changelog.tip()
    tip_ctx = repository.changectx( tip_changeset )
    return "%s:%s" % ( str( tip_ctx.rev() ), tip_ctx.parents()[0] )
def get_user( trans, id ):
    """Get a user from the database"""
    return trans.sa_session.query( trans.model.User ).get( trans.security.decode_id( id ) )
def hg_add( trans, current_working_dir, cloned_repo_dir ):
    # Add files to a cloned repository.  If they're already tracked, this should do nothing.
    os.chdir( cloned_repo_dir )
    os.system( 'hg add > /dev/null 2>&1' )
    os.chdir( current_working_dir )
def hg_clone( trans, repository, current_working_dir ):
    # Make a clone of a repository in a temporary location.
    repo_dir = repository.repo_path
    tmp_dir = tempfile.mkdtemp()
    tmp_archive_dir = os.path.join( tmp_dir, 'tmp_archive_dir' )
    if not os.path.exists( tmp_archive_dir ):
        os.makedirs( tmp_archive_dir )
    cmd = "hg clone %s > /dev/null 2>&1" % os.path.abspath( repo_dir )
    os.chdir( tmp_archive_dir )
    os.system( cmd )
    os.chdir( current_working_dir )
    cloned_repo_dir = os.path.join( tmp_archive_dir, 'repo_%d' % repository.id )
    return tmp_dir, cloned_repo_dir
def hg_commit( commit_message, current_working_dir, cloned_repo_dir ):
    # Commit a change set to a cloned repository.
    if not commit_message:
        commit_message = "No commit message"
    os.chdir( cloned_repo_dir )
    os.system( "hg commit -m '%s' > /dev/null 2>&1" % commit_message )
    os.chdir( current_working_dir )
def hg_push( trans, repository, current_working_dir, cloned_repo_dir ):
    # Push a change set from a cloned repository to a master repository.
    repo_dir = repository.repo_path
    repo = hg.repository( ui.ui(), repo_dir )
    # We want these change sets to be associated with the owner of the repository, so we'll
    # set the HGUSER environment variable accordingly.
    os.environ[ 'HGUSER' ] = trans.user.username
    cmd = "hg push %s > /dev/null 2>&1" % os.path.abspath( repo_dir )
    os.chdir( cloned_repo_dir )
    os.system( cmd )
    os.chdir( current_working_dir )
def hg_remove( file_path, current_working_dir, cloned_repo_dir ):
    # Remove a file path from a cloned repository.  Since mercurial doesn't track
    # directories (only files), directories are automatically removed when they
    # become empty.
    abs_file_path = os.path.join( cloned_repo_dir, file_path )
    if os.path.exists( abs_file_path ):
        cmd = 'hg remove %s > /dev/null 2>&1' % file_path
        os.chdir( cloned_repo_dir )
        os.system( cmd )
        os.chdir( current_working_dir )
def update_for_browsing( repository, current_working_dir ):
    # Make a copy of a repository's files for browsing.
    repo_dir = repository.repo_path
    os.chdir( repo_dir )
    os.system( 'hg update > /dev/null 2>&1' )
    os.chdir( current_working_dir )
