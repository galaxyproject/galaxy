"""
Galaxy Tool Shed data model classes

Naming: try to use class names that have a distinct plural form so that
the relationship cardinalities are obvious (e.g. prefer Dataset to Data)
"""
import os.path, os, errno, sys, codecs, operator, logging, tarfile, mimetypes, ConfigParser
from galaxy import util
from galaxy.util.bunch import Bunch
from galaxy.util.hash_util import *
from galaxy.web.form_builder import *

from galaxy import eggs
eggs.require('mercurial')
from mercurial import hg, ui

log = logging.getLogger( __name__ )

class User( object ):
    def __init__( self, email=None, password=None ):
        self.email = email
        self.password = password
        self.external = False
        self.deleted = False
        self.purged = False
        self.username = None
        self.new_repo_alert = False
    def set_password_cleartext( self, cleartext ):
        """Set 'self.password' to the digest of 'cleartext'."""
        self.password = new_secure_hash( text_type=cleartext )
    def check_password( self, cleartext ):
        """Check if 'cleartext' matches 'self.password' when hashed."""
        return self.password == new_secure_hash( text_type=cleartext )
    def get_disk_usage( self, nice_size=False ):
        return 0
    def set_disk_usage( self, bytes ):
        pass
    total_disk_usage = property( get_disk_usage, set_disk_usage )
    @property
    def nice_total_disk_usage( self ):
        return 0

class Group( object ):
    def __init__( self, name = None ):
        self.name = name
        self.deleted = False

class Role( object ):
    private_id = None
    types = Bunch( 
        PRIVATE = 'private',
        SYSTEM = 'system',
        USER = 'user',
        ADMIN = 'admin',
        SHARING = 'sharing'
    )
    def __init__( self, name="", description="", type="system", deleted=False ):
        self.name = name
        self.description = description
        self.type = type
        self.deleted = deleted

class UserGroupAssociation( object ):
    def __init__( self, user, group ):
        self.user = user
        self.group = group

class UserRoleAssociation( object ):
    def __init__( self, user, role ):
        self.user = user
        self.role = role

class GroupRoleAssociation( object ):
    def __init__( self, group, role ):
        self.group = group
        self.role = role

class GalaxySession( object ):
    def __init__( self, 
                  id=None, 
                  user=None, 
                  remote_host=None, 
                  remote_addr=None, 
                  referer=None, 
                  current_history=None, 
                  session_key=None, 
                  is_valid=False, 
                  prev_session_id=None ):
        self.id = id
        self.user = user
        self.remote_host = remote_host
        self.remote_addr = remote_addr
        self.referer = referer
        self.current_history = current_history
        self.session_key = session_key
        self.is_valid = is_valid
        self.prev_session_id = prev_session_id

class Repository( object ):
    file_states = Bunch( NORMAL = 'n',
                         NEEDS_MERGING = 'm',
                         MARKED_FOR_REMOVAL = 'r',
                         MARKED_FOR_ADDITION = 'a',
                         NOT_TRACKED = '?' )
    def __init__( self, name=None, description=None, long_description=None, user_id=None, private=False, email_alerts=None, times_downloaded=0 ):
        self.name = name or "Unnamed repository"
        self.description = description
        self.long_description = long_description
        self.user_id = user_id
        self.private = private
        self.email_alerts = email_alerts
        self.times_downloaded = times_downloaded
    @property
    def repo_path( self ):
        # Repository locations on disk are defined in the hgweb.config file
        # in the Galaxy install directory.  An entry looks something like:
        # repos/test/mira_assembler = database/community_files/000/repo_123
        # TODO: handle this using the mercurial api.
        lhs = "repos/%s/%s" % ( self.user.username, self.name )
        hgweb_config = "%s/hgweb.config" %  os.getcwd()
        if not os.path.exists( hgweb_config ):
            raise Exception( "Required file hgweb.config does not exist in directory %s" % os.getcwd() )
        config = ConfigParser.ConfigParser()
        config.read( hgweb_config )
        for option in config.options( "paths" ):
            if option == lhs:
                return config.get( "paths", option )
        raise Exception( "Entry for repository %s missing in %s/hgweb.config file." % ( lhs, os.getcwd() ) )
    @property
    def revision( self ):
        repo = hg.repository( ui.ui(), self.repo_path )
        tip_ctx = repo.changectx( repo.changelog.tip() )
        return "%s:%s" % ( str( tip_ctx.rev() ), str( repo.changectx( repo.changelog.tip() ) ) )
    @property
    def tip( self ):
        repo = hg.repository( ui.ui(), self.repo_path )
        return str( repo.changectx( repo.changelog.tip() ) )
    @property
    def is_new( self ):
        repo = hg.repository( ui.ui(), self.repo_path )
        tip_ctx = repo.changectx( repo.changelog.tip() )
        return tip_ctx.rev() < 0
    @property
    def allow_push( self ):
        repo = hg.repository( ui.ui(), self.repo_path )
        return repo.ui.config( 'web', 'allow_push' )
    def set_allow_push( self, usernames, remove_auth='' ):
        allow_push = util.listify( self.allow_push )
        if remove_auth:
            allow_push.remove( remove_auth )
        else:
            for username in util.listify( usernames ):
                if username not in allow_push:
                    allow_push.append( username )
        allow_push = '%s\n' % ','.join( allow_push )
        repo = hg.repository( ui.ui(), path=self.repo_path )
        # Why doesn't the following work?
        #repo.ui.setconfig( 'web', 'allow_push', allow_push )
        lines = repo.opener( 'hgrc', 'rb' ).readlines()
        fp = repo.opener( 'hgrc', 'wb' )
        for line in lines:
            if line.startswith( 'allow_push' ):
                fp.write( 'allow_push = %s' % allow_push )
            else:
                fp.write( line )
        fp.close()

class RepositoryMetadata( object ):
    def __init__( self, repository_id=None, changeset_revision=None, metadata=None, tool_versions=None, malicious=False ):
        self.repository_id = repository_id
        self.changeset_revision = changeset_revision
        self.metadata = metadata or dict()
        self.tool_versions = tool_versions or dict()
        self.malicious = malicious
    
class ItemRatingAssociation( object ):
    def __init__( self, id=None, user=None, item=None, rating=0, comment='' ):
        self.id = id
        self.user = user
        self.item = item
        self.rating = rating
        self.comment = comment
    def set_item( self, item ):
        """ Set association's item. """
        pass

class RepositoryRatingAssociation( ItemRatingAssociation ):
    def set_item( self, repository ):
        self.repository = repository

class Category( object ):
    def __init__( self, name=None, description=None, deleted=False ):
        self.name = name
        self.description = description
        self.deleted = deleted

class RepositoryCategoryAssociation( object ):
    def __init__( self, repository=None, category=None ):
        self.repository = repository
        self.category = category

class Tag ( object ):
    def __init__( self, id=None, type=None, parent_id=None, name=None ):
        self.id = id
        self.type = type
        self.parent_id = parent_id
        self.name = name
    def __str__ ( self ):
        return "Tag(id=%s, type=%i, parent_id=%s, name=%s)" %  ( self.id, self.type, self.parent_id, self.name )

class ItemTagAssociation ( object ):
    def __init__( self, id=None, user=None, item_id=None, tag_id=None, user_tname=None, value=None ):
        self.id = id
        self.user = user
        self.item_id = item_id
        self.tag_id = tag_id
        self.user_tname = user_tname
        self.value = None
        self.user_value = None

class Workflow( object ):
    def __init__( self ):
        self.user = None
        self.name = None
        self.has_cycles = None
        self.has_errors = None
        self.steps = []

class WorkflowStep( object ):
    def __init__( self ):
        self.id = None
        self.type = None
        self.name = None
        self.tool_id = None
        self.tool_inputs = None
        self.tool_errors = None
        self.position = None
        self.input_connections = []
        #self.output_connections = []
        self.config = None

class WorkflowStepConnection( object ):
    def __init__( self ):
        self.output_step = None
        self.output_name = None
        self.input_step = None
        self.input_name = None

## ---- Utility methods -------------------------------------------------------
def sort_by_attr( seq, attr ):
    """
    Sort the sequence of objects by object's attribute
    Arguments:
    seq  - the list or any sequence (including immutable one) of objects to sort.
    attr - the name of attribute to sort by
    """
    # Use the "Schwartzian transform"
    # Create the auxiliary list of tuples where every i-th tuple has form
    # (seq[i].attr, i, seq[i]) and sort it. The second item of tuple is needed not
    # only to provide stable sorting, but mainly to eliminate comparison of objects
    # (which can be expensive or prohibited) in case of equal attribute values.
    intermed = map( None, map( getattr, seq, ( attr, ) * len( seq ) ), xrange( len( seq ) ), seq )
    intermed.sort()
    return map( operator.getitem, intermed, ( -1, ) * len( intermed ) )
def directory_hash_id( id ):
    s = str( id )
    l = len( s )
    # Shortcut -- ids 0-999 go under ../000/
    if l < 4:
        return [ "000" ]
    # Pad with zeros until a multiple of three
    padded = ( ( ( 3 - len( s ) ) % 3 ) * "0" ) + s
    # Drop the last three digits -- 1000 files per directory
    padded = padded[:-3]
    # Break into chunks of three
    return [ padded[i*3:(i+1)*3] for i in range( len( padded ) // 3 ) ]
