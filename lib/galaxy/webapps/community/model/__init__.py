"""
Galaxy Community Space data model classes

Naming: try to use class names that have a distinct plural form so that
the relationship cardinalities are obvious (e.g. prefer Dataset to Data)
"""
import os.path, os, errno, sys, codecs, operator, tempfile, logging, tarfile
from galaxy.util.bunch import Bunch
from galaxy import util
from galaxy.util.hash_util import *
from galaxy.web.form_builder import *
log = logging.getLogger( __name__ )
from sqlalchemy.orm import object_session

class User( object ):
    def __init__( self, email=None, password=None ):
        self.email = email
        self.password = password
        self.external = False
        self.deleted = False
        self.purged = False
        self.username = None
        # Relationships
        self.tools = []
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

class Tool( object ):
    file_path = '/tmp'
    def __init__( self, guid=None, tool_id=None, name=None, description=None, user_description=None, category=None, version=None, user_id=None, external_filename=None ):
        self.guid = guid
        self.tool_id = tool_id
        self.name = name or "Unnamed tool"
        self.description = description
        self.user_description = user_description
        self.version = version or "1.0.0"
        self.user_id = user_id
        self.external_filename = external_filename
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

class Tag ( object ):
    def __init__( self, id=None, type=None, parent_id=None, name=None ):
        self.id = id
        self.type = type
        self.parent_id = parent_id
        self.name = name
    def __str__ ( self ):
        return "Tag(id=%s, type=%i, parent_id=%s, name=%s)" %  ( self.id, self.type, self.parent_id, self.name )
    
class Category( object ):
    def __init__( self, name=None, description=None, deleted=False ):
        self.name = name
        self.description = description
        self.deleted = deleted

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

class ToolCategoryAssociation( object ):
    def __init__( self, tool=None, category=None ):
        self.tool = tool
        self.category = category

## ---- Utility methods -------------------------------------------------------

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


