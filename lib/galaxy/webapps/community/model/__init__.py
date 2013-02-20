"""
Galaxy Tool Shed data model classes

Naming: try to use class names that have a distinct plural form so that
the relationship cardinalities are obvious (e.g. prefer Dataset to Data)
"""
import os.path, os, errno, sys, codecs, operator, logging, tarfile, mimetypes, ConfigParser
from galaxy import util
from galaxy.util.bunch import Bunch
from galaxy.util.hash_util import new_secure_hash
from galaxy.web.form_builder import *
from galaxy.model.item_attrs import APIItem

from galaxy import eggs
eggs.require('mercurial')
from mercurial import hg, ui

log = logging.getLogger( __name__ )

class APIKeys( object ):
    pass

class User( object, APIItem ):
    api_collection_visible_keys = ( 'id', 'email' )
    api_element_visible_keys = ( 'id', 'email', 'username' )
    def __init__( self, email=None, password=None ):
        self.email = email
        self.password = password
        self.external = False
        self.deleted = False
        self.purged = False
        self.username = None
        self.new_repo_alert = False
    def all_roles( self ):
        roles = [ ura.role for ura in self.roles ]
        for group in [ uga.group for uga in self.groups ]:
            for role in [ gra.role for gra in group.roles ]:
                if role not in roles:
                    roles.append( role )
        return roles
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

class Group( object, APIItem ):
    api_collection_visible_keys = ( 'id', 'name' )
    api_element_visible_keys = ( 'id', 'name' )
    def __init__( self, name = None ):
        self.name = name
        self.deleted = False

class Role( object, APIItem ):
    api_collection_visible_keys = ( 'id', 'name' )
    api_element_visible_keys = ( 'id', 'name', 'description', 'type' )
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

class Repository( object, APIItem ):
    api_collection_visible_keys = ( 'id', 'name' )
    api_element_visible_keys = ( 'id', 'name', 'description' )
    file_states = Bunch( NORMAL = 'n',
                         NEEDS_MERGING = 'm',
                         MARKED_FOR_REMOVAL = 'r',
                         MARKED_FOR_ADDITION = 'a',
                         NOT_TRACKED = '?' )
    def __init__( self, name=None, description=None, long_description=None, user_id=None, private=False, email_alerts=None, times_downloaded=0, deprecated=False ):
        self.name = name or "Unnamed repository"
        self.description = description
        self.long_description = long_description
        self.user_id = user_id
        self.private = private
        self.email_alerts = email_alerts
        self.times_downloaded = times_downloaded
        self.deprecated = deprecated
    def repo_path( self, app ):
        return app.hgweb_config_manager.get_entry( os.path.join( "repos", self.user.username, self.name ) )
    def revision( self, app ):
        repo = hg.repository( ui.ui(), self.repo_path( app ) )
        tip_ctx = repo.changectx( repo.changelog.tip() )
        return "%s:%s" % ( str( tip_ctx.rev() ), str( repo.changectx( repo.changelog.tip() ) ) )
    def tip( self, app ):
        repo = hg.repository( ui.ui(), self.repo_path( app ) )
        return str( repo.changectx( repo.changelog.tip() ) )
    def is_new( self, app ):
        repo = hg.repository( ui.ui(), self.repo_path( app ) )
        tip_ctx = repo.changectx( repo.changelog.tip() )
        return tip_ctx.rev() < 0
    def allow_push( self, app ):
        repo = hg.repository( ui.ui(), self.repo_path( app ) )
        return repo.ui.config( 'web', 'allow_push' )
    def set_allow_push( self, app, usernames, remove_auth='' ):
        allow_push = util.listify( self.allow_push( app ) )
        if remove_auth:
            allow_push.remove( remove_auth )
        else:
            for username in util.listify( usernames ):
                if username not in allow_push:
                    allow_push.append( username )
        allow_push = '%s\n' % ','.join( allow_push )
        repo = hg.repository( ui.ui(), path=self.repo_path( app ) )
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

class RepositoryMetadata( object, APIItem ):
    api_collection_visible_keys = ( 'id', 'repository_id', 'changeset_revision', 'malicious', 'downloadable' )
    api_element_visible_keys = ( 'id', 'repository_id', 'changeset_revision', 'malicious', 'downloadable' )
    def __init__( self, repository_id=None, changeset_revision=None, metadata=None, tool_versions=None, malicious=False, downloadable=False ):
        self.repository_id = repository_id
        self.changeset_revision = changeset_revision
        self.metadata = metadata or dict()
        self.tool_versions = tool_versions or dict()
        self.malicious = malicious
        self.downloadable = downloadable
    def get_api_value( self, view='collection', value_mapper=None ):
        if value_mapper is None:
            value_mapper = {}
        rval = {}
        try:
            visible_keys = self.__getattribute__( 'api_' + view + '_visible_keys' )
        except AttributeError:
            raise Exception( 'Unknown API view: %s' % view )
        for key in visible_keys:
            try:
                rval[ key ] = self.__getattribute__( key )
                if key in value_mapper:
                    rval[ key ] = value_mapper.get( key )( rval[ key ] )
            except AttributeError:
                rval[ key ] = None
        return rval

class RepositoryReview( object, APIItem ):
    api_collection_visible_keys = ( 'id', 'repository_id', 'changeset_revision', 'user_id', 'rating' )
    api_element_visible_keys = ( 'id', 'repository_id', 'changeset_revision', 'user_id', 'rating' )
    approved_states = Bunch( NO='no', YES='yes' )
    def __init__( self, repository_id=None, changeset_revision=None, user_id=None, rating=None, deleted=False ):
        self.repository_id = repository_id
        self.changeset_revision = changeset_revision
        self.user_id = user_id
        self.rating = rating
        self.deleted = deleted

class ComponentReview( object, APIItem ):
    api_collection_visible_keys = ( 'id', 'repository_review_id', 'component_id', 'private', 'approved', 'rating', 'deleted' )
    api_element_visible_keys = ( 'id', 'repository_review_id', 'component_id', 'private', 'approved', 'rating', 'deleted' )
    approved_states = Bunch( NO='no', YES='yes', NA='not_applicable' )
    def __init__( self, repository_review_id=None, component_id=None, comment=None, private=False, approved=False, rating=None, deleted=False ):
        self.repository_review_id = repository_review_id
        self.component_id = component_id
        self.comment = comment
        self.private = private
        self.approved = approved
        self.rating = rating
        self.deleted = deleted

class Component( object ):
    def __init__( self, name=None, description=None ):
        self.name = name
        self.description = description

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

class Category( object, APIItem ):
    api_collection_visible_keys = ( 'id', 'name', 'description', 'deleted' )
    api_element_visible_keys = ( 'id', 'name', 'description', 'deleted' )
    def __init__( self, name=None, description=None, deleted=False ):
        self.name = name
        self.description = description
        self.deleted = deleted

class RepositoryCategoryAssociation( object ):
    def __init__( self, repository=None, category=None ):
        self.repository = repository
        self.category = category

class Tag( object ):
    def __init__( self, id=None, type=None, parent_id=None, name=None ):
        self.id = id
        self.type = type
        self.parent_id = parent_id
        self.name = name
    def __str__ ( self ):
        return "Tag(id=%s, type=%i, parent_id=%s, name=%s)" %  ( self.id, self.type, self.parent_id, self.name )

class ItemTagAssociation( object ):
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
