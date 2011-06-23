"""
Galaxy Tool Shed data model classes

Naming: try to use class names that have a distinct plural form so that
the relationship cardinalities are obvious (e.g. prefer Dataset to Data)
"""
import os.path, os, errno, sys, codecs, operator, tempfile, logging, tarfile, mimetypes, ConfigParser
from galaxy.util.bunch import Bunch
from galaxy.util.hash_util import *
from galaxy.web.form_builder import *
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
    def set_password_cleartext( self, cleartext ):
        """Set 'self.password' to the digest of 'cleartext'."""
        self.password = new_secure_hash( text_type=cleartext )
    def check_password( self, cleartext ):
        """Check if 'cleartext' matches 'self.password' when hashed."""
        return self.password == new_secure_hash( text_type=cleartext )

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
    def __init__( self, name=None, description=None, user_id=None, private=False, email_alerts=None ):
        self.name = name or "Unnamed repository"
        self.description = description
        self.user_id = user_id
        self.private = private
        self.email_alerts = email_alerts
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
    def is_new( self ):
        repo = hg.repository( ui.ui(), self.repo_path )
        tip_ctx = repo.changectx( repo.changelog.tip() )
        return tip_ctx.rev() < 0
class Tool( object ):
    file_path = '/tmp' # Overridden in mapping.__init__()
    states = Bunch( NEW = 'new',
                    ERROR = 'error',
                    DELETED = 'deleted',
                    WAITING = 'waiting',
                    APPROVED = 'approved',
                    REJECTED = 'rejected',
                    ARCHIVED = 'archived' )
    def __init__( self, guid=None, tool_id=None, name=None, description=None, user_description=None, 
                  category=None, version=None, user_id=None, external_filename=None, suite=False ):
        self.guid = guid
        self.tool_id = tool_id
        self.name = name or "Unnamed tool"
        self.description = description
        self.user_description = user_description
        self.version = version or "1.0.0"
        self.user_id = user_id
        self.external_filename = external_filename
        self.deleted = False
        self.__extension = None
        self.suite = suite
    def get_file_name( self ):
        if not self.external_filename:
            assert self.id is not None, "ID must be set before filename used (commit the object)"
            dir = os.path.join( self.file_path, 'tools', *directory_hash_id( self.id ) )
            # Create directory if it does not exist
            if not os.path.exists( dir ):
                os.makedirs( dir )
            # Return filename inside hashed directory
            filename = os.path.join( dir, "tool_%d.dat" % self.id )
        else:
            filename = self.external_filename
        # Make filename absolute
        return os.path.abspath( filename )
    def set_file_name( self, filename ):
        if not filename:
            self.external_filename = None
        else:
            self.external_filename = filename
    file_name = property( get_file_name, set_file_name )
    def create_from_datatype( self, datatype_bunch ):
        # TODO: ensure guid is unique and generate a new one if not.
        self.guid = datatype_bunch.guid
        self.tool_id = datatype_bunch.id
        self.name = datatype_bunch.name
        self.description = datatype_bunch.description
        self.version = datatype_bunch.version
        self.user_id = datatype_bunch.user.id
        self.suite = datatype_bunch.suite
    @property
    def state( self ):
        latest_event = self.latest_event
        if latest_event:
            return latest_event.state
        return None
    @property
    def latest_event( self ):
        if self.events:
            events = [ tea.event for tea in self.events ]
            # Get the last event that occurred ( events mapper is sorted descending )
            return events[0]
        return None
    # Tool states
    @property
    def is_new( self ):
        return self.state == self.states.NEW
    @property
    def is_error( self ):
        return self.state == self.states.ERROR
    @property
    def is_deleted( self ):
        return self.state == self.states.DELETED
    @property
    def is_waiting( self ):
        return self.state == self.states.WAITING
    @property
    def is_approved( self ):
        return self.state == self.states.APPROVED
    @property
    def is_rejected( self ):
        return self.state == self.states.REJECTED
    @property
    def is_archived( self ):
        return self.state == self.states.ARCHIVED
    def get_state_message( self ):
        if self.is_suite:
            label = 'tool suite'
        else:
            label = 'tool'
        if self.is_new:
            return '<font color="red"><b><i>This is an unsubmitted version of this %s</i></b></font>' % label
        if self.is_error:
            return '<font color="red"><b><i>This %s is in an error state</i></b></font>' % label
        if self.is_deleted:
            return '<font color="red"><b><i>This is a deleted version of this %s</i></b></font>' % label
        if self.is_waiting:
            return '<font color="red"><b><i>This version of this %s is awaiting administrative approval</i></b></font>' % label
        if self.is_approved:
            return '<b><i>This is the latest approved version of this %s</i></b>' % label
        if self.is_rejected:
            return '<font color="red"><b><i>This version of this %s has been rejected by an administrator</i></b></font>' % label
        if self.is_archived:
            return '<font color="red"><b><i>This is an archived version of this %s</i></b></font>' % label
    @property
    def extension( self ):
        # if instantiated via a query, this unmapped property won't exist
        if '_Tool__extension' not in dir( self ):
            self.__extension = None
        if self.__extension is None:
            head = open( self.file_name, 'rb' ).read( 4 )
            try:
                assert head[:3] == 'BZh'
                assert int( head[-1] ) in range( 0, 10 )
                self.__extension = 'tar.bz2'
            except AssertionError:
                pass
        if self.__extension is None:
            try:
                assert head[:2] == '\037\213'
                self.__extension = 'tar.gz'
            except:
                pass
        if self.__extension is None:
            self.__extension = 'tar'
        return self.__extension
    @property
    def is_suite( self ):
        return self.suite
    @property
    def label( self ):
        if self.is_suite:
            return 'tool suite'
        else:
            return 'tool'
    @property
    def type( self ):
        # Hack
        if self.is_suite:
            return 'toolsuite'
        return 'tool'
    @property
    def download_file_name( self ):
        return '%s_%s.%s' % ( self.tool_id, self.version, self.extension )
    @property
    def mimetype( self ):
        return mimetypes.guess_type( self.download_file_name )[0]

class Event( object ):
    def __init__( self, state=None, comment='' ):
        self.state = state
        self.comment = comment

class ToolEventAssociation( object ):
    def __init__( self, tool=None, event=None ):
        self.tool = tool
        self.event = event

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

class ToolRatingAssociation( ItemRatingAssociation ):
    def set_item( self, tool ):
        self.tool = tool

class RepositoryRatingAssociation( ItemRatingAssociation ):
    def set_item( self, repository ):
        self.repository = repository

class Category( object ):
    def __init__( self, name=None, description=None, deleted=False ):
        self.name = name
        self.description = description
        self.deleted = deleted

class ToolCategoryAssociation( object ):
    def __init__( self, tool=None, category=None ):
        self.tool = tool
        self.category = category

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
        
class ToolTagAssociation ( ItemTagAssociation ):
    pass

class ToolAnnotationAssociation( object ):
    pass

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
