"""
Galaxy data model classes

Naming: try to use class names that have a distinct plural form so that
the relationship cardinalities are obvious (e.g. prefer Dataset to Data)
"""

import os.path, os, errno
import sha
import galaxy.datatypes
from galaxy.util.bunch import Bunch
from galaxy import util
import tempfile
import galaxy.datatypes.registry
from galaxy.datatypes.metadata import MetadataCollection

import logging
log = logging.getLogger( __name__ )

datatypes_registry = galaxy.datatypes.registry.Registry() #Default Value Required for unit tests

def set_datatypes_registry( d_registry ):
    """
    Set up datatypes_registry
    """
    global datatypes_registry
    datatypes_registry = d_registry

class User( object ):
    def __init__( self, email=None, password=None, groups = [], roles = [], default_groups = [], default_roles = [] ):
        self.email = email
        self.password = password
        self.external = False
        # Relationships
        self.histories = []
        if not groups:
            groups.append( GalaxyGroup.get( GalaxyGroup.public_id ) )
            default_groups.append( groups[-1] )
            default_groups.append( self.create_private_group() )
        group_id_added = []
        for group in groups:
            if group.id not in group_id_added:
                group.add_user( self )
                group_id_added.append( group.id )
        group_id_added = []
        for group in default_groups:
            if group.id not in group_id_added:
                user_group_assoc = DefaultUserGroupAssociation( self, group )
                user_group_assoc.flush()
                group_id_added.append( group.id )
        role_id_added = []
        for role in roles:
            if role.id not in role_id_added:
                role.add_user( self )
                role_id_added.append( role.id )
        role_id_added = []
        for role in default_roles:
            if role.id not in role_id_added:
                role_group_assoc = DefaultUserRoleAssociation( self, role )
                role_group_assoc.flush()
                role_id_added.append( role.id )
    def set_password_cleartext( self, cleartext ):
        """Set 'self.password' to the digest of 'cleartext'."""
        self.password = sha.new( cleartext ).hexdigest()
    def check_password( self, cleartext ):
        """Check if 'cleartext' matches 'self.password' when hashed."""
        return self.password == sha.new( cleartext ).hexdigest()
    def create_private_group( self ):
        #create private group
        group = GalaxyGroup( self.email, priority = 10 )
        group.flush()
        #create private dataset access role
        role = AccessRole( "%s dataset access" % self.email, list( Dataset.access_actions.__dict__.values() ), priority = 1 )
        role.flush()
        #add role to group
        group.add_role( role )
        
        #create roles for user modification of role
        user_role = AccessRole( "%s role modification" % self.email, list( AccessRole.access_actions.__dict__.values() ) )
        user_role.flush()
        #add role to user
        user_role.add_user( self )
        #add role to role
        role.add_role( user_role )
        
        #create roles for user modification of group
        group_role = AccessRole( "%s group modification" % self.email, list( GalaxyGroup.access_actions.__dict__.values() ) )
        group_role.flush()
        #add role to group
        group.add_access_role( group_role )
        #associate role and user
        group_role.add_user( self )
        
        #add user to group
        group.add_user( self )
        group.flush()
        return group
    def add_group( self, group ):
        return group.add_user( self )
    def has_group( self, check_group ):
        return bool( UserGroupAssociation.get_by( group_id = check_group.id, user_id = self.id ) )
    def has_role( self, check_role ):
        return bool( UserRoleAssociation.get_by( role_id = check_role.id, user_id = self.id ) )
    def set_default_access( self, groups = None, roles = None, history = False, dataset = False ):
        if groups is not None:
            for assoc in self.default_groups: #this is the association not the actual group
                assoc.delete()
                assoc.flush()
            for group in groups:
                assoc = DefaultUserGroupAssociation( self, group )
                assoc.flush()
        if roles is not None:
            for assoc in self.default_roles: #this is the association not the actual group
                assoc.delete()
                assoc.flush()
            for role in roles:
                assoc = DefaultUserRoleAssociation( self, role )
                assoc.flush()
        if history:
            for history in self.histories:
                history.set_default_access( groups = groups, roles = roles, dataset = dataset )
    
class Job( object ):
    """
    A job represents a request to run a tool given input datasets, tool 
    parameters, and output datasets.
    """
    states = Bunch( NEW = 'new',
                    WAITING = 'waiting',
                    QUEUED = 'queued',
                    RUNNING = 'running',
                    OK = 'ok',
                    ERROR = 'error',
                    DELETED = 'deleted' )
    def __init__( self ):
        self.session_id = None
        self.tool_id = None
        self.tool_version = None
        self.command_line = None
        self.param_filename = None
        self.parameters = []
        self.input_datasets = []
        self.output_datasets = []
        self.state = Job.states.NEW
        self.info = None
        self.job_runner_name = None
        self.job_runner_external_id = None
    def add_parameter( self, name, value ):
        self.parameters.append( JobParameter( name, value ) )
    def add_input_dataset( self, name, dataset ):
        self.input_datasets.append( JobToInputDatasetAssociation( name, dataset ) )
    def add_output_dataset( self, name, dataset ):
        self.output_datasets.append( JobToOutputDatasetAssociation( name, dataset ) )
    def set_state( self, state ):
        self.state = state
        # For historical reasons state propogates down to datasets
        for da in self.output_datasets:
            da.dataset.state = state
    def get_param_values( self, app ):
        """
        Read encoded parameter values from the database and turn back into a
        dict of tool parameter values.
        """
        param_dict = dict( [ ( p.name, p.value ) for p in self.parameters ] )
        tool = app.toolbox.tools_by_id[self.tool_id]
        param_dict = tool.params_from_strings( param_dict, app )
        return param_dict
                
class JobParameter( object ):
    def __init__( self, name, value ):
        self.name = name
        self.value = value
          
class JobToInputDatasetAssociation( object ):
    def __init__( self, name, dataset ):
        self.name = name
        self.dataset = dataset
        
class JobToOutputDatasetAssociation( object ):
    def __init__( self, name, dataset ):
        self.name = name
        self.dataset = dataset

class AccessRole( object ):
    dataset_actions = Bunch( VIEW = 'dataset_view', #viewing/downloading
                    USE = 'dataset_use', #use in jobs
                    ADD_ROLE = 'dataset_add_role', #dataset can be added to roles
                    REMOVE_ROLE = 'dataset_remove_role', #dataset can be removed from roles
                    ADD_GROUP = 'dataset_add_group', #dataset can be added to groups
                    REMOVE_GROUP = 'dataset_remove_group' ) #dataset can be removed from groups
    role_actions = Bunch( ADD_DATASET = 'role_add_dataset', #add role to dataset
                    REMOVE_DATASET = 'role_remove_dataset', #remove role from dataset
                    DELETE = 'role_delete', #delete a role
                    MODIFY = 'role_modify', #change a role's actions,
                    ADD_GROUP = 'role_add_group', #add role to a group
                    REMOVE_GROUP = 'role_remove_group' ) #remove role from a group
    group_actions = Bunch( ADD_DATASET = 'group_add_dataset', #add group to dataset
                    REMOVE_DATASET = 'group_remove_dataset', #remove dataset from group
                    DELETE = 'group_delete', #delete a group
                    ADD_ROLE = 'group_add_role', #add role to group
                    REMOVE_ROLE = 'group_remove_role', #remove role from group
                    ADD_USER = 'group_add_user' ) #add users to group
    
    access_actions = role_actions
    
    def __init__( self, name, actions, priority = 0 ):
        self.name = name
        if not isinstance( actions, list ):
            actions = [ actions ]
        self.actions = actions
        self.priority = priority
    def add_user( self, user ):
        assoc = UserRoleAssociation( user, self )
        assoc.flush()
        return assoc
    def add_group( self, group ):
        assoc = GroupRoleAssociation( group, self )
        assoc.flush()
        return assoc
    def add_role( self, role ):
        assoc = RoleRoleAssociation( role, self )
        assoc.flush()
        return assoc
    def add_dataset( self, dataset ):
        assoc = RoleDatasetAssociation( self, dataset )
        assoc.flush()
        return assoc

class GalaxyGroup( object ):
    public_id = None
    access_actions = AccessRole.group_actions
    def __init__( self, name, priority = 0 ):
        self.name = name
        self.priority = priority
    def add_user( self, user ):
        assoc = UserGroupAssociation( user, self )
        assoc.flush()
        return assoc
    def add_role( self, role ):
        return role.add_group( self )
    def add_access_role( self, role ):
        assoc = GroupRoleAccessAssociation( self, role )
        assoc.flush()
        return assoc
    def add_dataset( self, dataset ):
        assoc = GroupDatasetAssociation( self, dataset )
        assoc.flush()
        return assoc

class UserGroupAssociation( object ):
    def __init__( self, user, group ):
        self.user = user
        self.group = group

class RoleRoleAssociation( object ):
    def __init__( self, role, target_role ):
        self.role = role
        self.target_role = target_role

class GroupRoleAccessAssociation( object ):
    def __init__( self, group, role ):
        self.group = group
        self.role = role

class GroupRoleAssociation( object ):
    def __init__( self, group, role ):
        self.group = group
        self.role = role

class UserRoleAssociation( object ):
    def __init__( self, user, role ):
        self.user = user
        self.role = role

class GroupDatasetAssociation( object ):
    def __init__( self, group, dataset ):
        if isinstance( group, GroupDatasetAssociation ) or isinstance( group, DefaultUserGroupAssociation ) or isinstance( group, DefaultHistoryGroupAssociation ):
            group = group.group
        self.group = group
        
        if isinstance( dataset, HistoryDatasetAssociation ):
            dataset = dataset.dataset
        self.dataset = dataset

class RoleDatasetAssociation( object ):
    def __init__( self, role, dataset ):
        if isinstance( role, RoleDatasetAssociation ) or isinstance( role, DefaultUserRoleAssociation ) or isinstance( role, DefaultHistoryRoleAssociation ):
            role = role.role
        self.role = role
        
        if isinstance( dataset, HistoryDatasetAssociation ):
            dataset = dataset.dataset
        self.dataset = dataset

class DefaultUserRoleAssociation( object ):
    def __init__( self, user, role ):
        if isinstance( role, RoleDatasetAssociation ) or isinstance( role, DefaultUserRoleAssociation ) or isinstance( role, DefaultHistoryRoleAssociation ):
            role = role.role
        self.user = user
        self.role = role

class DefaultUserGroupAssociation( object ):
    def __init__( self, user, group ):
        if isinstance( group, GroupDatasetAssociation ) or isinstance( group, DefaultUserGroupAssociation ) or isinstance( group, DefaultHistoryGroupAssociation ):
            group = group.group
        self.user = user
        self.group = group

class DefaultHistoryRoleAssociation( object ):
    def __init__( self, history, role ):
        if isinstance( role, RoleDatasetAssociation ) or isinstance( role, DefaultUserRoleAssociation ) or isinstance( role, DefaultHistoryRoleAssociation ):
            role = role.role
        self.history = history
        self.role = role

class DefaultHistoryGroupAssociation( object ):
    def __init__( self, history, group ):
        if isinstance( group, GroupDatasetAssociation ) or isinstance( group, DefaultUserGroupAssociation ) or isinstance( group, DefaultHistoryGroupAssociation ):
            group = group.group
        self.history = history
        self.group = group

class Dataset( object ):
    states = Bunch( NEW = 'new',
                    QUEUED = 'queued',
                    RUNNING = 'running',
                    OK = 'ok',
                    EMPTY = 'empty',
                    ERROR = 'error',
                    DISCARDED = 'discarded' )
    access_actions = AccessRole.dataset_actions
    file_path = "/tmp/"
    engine = None
    def __init__( self, id=None, state=None, external_filename=None, extra_files_path=None, file_size=None, purgable=True, access_groups=[], access_roles=[] ):
        self.id = id
        self.state = state
        self.deleted = False
        self.purged = False
        self.purgable = purgable
        self.external_filename = external_filename
        self._extra_files_path = extra_files_path
        self.file_size = file_size
        if access_groups or access_roles:
            #self.flush()
            for group in access_groups:
                group.add_dataset( self )
                group.flush()
            for role in access_roles:
                role.add_dataset( self )
                role.flush()
    def get_file_name( self ):
        if not self.external_filename:
            assert self.id is not None, "ID must be set before filename used (commit the object)"
            # First try filename directly under file_path
            filename = os.path.join( self.file_path, "dataset_%d.dat" % self.id )
            # Only use that filename if it already exists (backward compatibility),
            # otherwise construct hashed path
            if not os.path.exists( filename ):
                dir = os.path.join( self.file_path, *directory_hash_id( self.id ) )
                # Create directory if it does not exist
                try:
                    os.makedirs( dir )
                except OSError, e:
                    # File Exists is okay, otherwise reraise
                    if e.errno != errno.EEXIST:
                        raise
                # Return filename inside hashed directory
                return os.path.abspath( os.path.join( dir, "dataset_%d.dat" % self.id ) )
        else:
            filename = self.external_filename
        # Make filename absolute
        return os.path.abspath( filename )
            
    def set_file_name ( self, filename ):
        if not filename:
            self.external_filename = None
        else:
            self.external_filename = filename
        
    file_name = property( get_file_name, set_file_name )
    
    @property
    def extra_files_path( self ):
        if self._extra_files_path: 
            path = self._extra_files_path
        else:
            path = os.path.join( self.file_path, "dataset_%d_files" % self.id )
            #only use path directly under self.file_path if it exists
            if not os.path.exists( path ):
                path = os.path.join( os.path.join( self.file_path, *directory_hash_id( self.id ) ), "dataset_%d_files" % self.id )
        # Make path absolute
        return os.path.abspath( path )
    
    def get_size( self ):
        """Returns the size of the data on disk"""
        if self.file_size:
            return self.file_size
        else:
            try:
                return os.path.getsize( self.file_name )
            except OSError:
                return 0
    def set_size( self ):
        """Returns the size of the data on disk"""
        try:
            self.file_size = os.path.getsize( self.file_name )
        except OSError:
            self.file_size = 0
    def has_data( self ):
        """Detects whether there is any data"""
        return self.get_size() > 0
    def mark_deleted( self, include_children=True ):
        self.deleted = True
    def allow_action( self, user, action ):
        """Returns true when user has permission to perform an action"""
        
        #if dataset is in public group, we always return true for viewing and using
        #this may need to change when the ability to alter groups and roles is allowed
        if action in [ self.access_actions.USE, self.access_actions.VIEW ] and GroupDatasetAssociation.get_by( group_id = GalaxyGroup.public_id, dataset_id = self.id ):
            return True
        elif user is not None:
            #loop through permissions and if allowed return true:
            #check roles associated directly with dataset first
            for role_dataset_assoc in self.roles:
                if action in role_dataset_assoc.role.actions and user.has_role( role_dataset_assoc.role ):
                    return True
            #check roles associated with dataset through groups
            for group_dataset_assoc in self.groups:
                if user.has_group( group_dataset_assoc.group ):
                    for group_role_assoc in group_dataset_assoc.group.roles:
                        if action in group_role_assoc.role.actions:
                            return True
        return False #no user and dataset not in public group, or user lacks permission
    def guess_derived_groups_roles( self, other_datasets = [] ):
        """Returns a list of output roles and groups based upon itself and provided datasets"""
        if not other_datasets:
            return [ data_group_assoc.group for data_group_assoc in self.groups ], [ data_role_assoc.role for data_role_assoc in self.roles ]
        access_roles = None
        priority_access_role = None
        access_groups = None
        priority_access_group = None
        for dataset in [ self ] + other_datasets:
            #determine access roles and groups for output datasets
            #roles and groups for output dataset is the intersection across all inputs
            #if we end up with no intersection between inputs, then we rely on priorities
            if isinstance( dataset, HistoryDatasetAssociation ):
                dataset = dataset.dataset
            roles = [ data_role_assoc.role for data_role_assoc in dataset.roles ]
            for role in roles:
                if priority_access_role is None or priority_access_role.priority < role.priority:
                    priority_access_role = role
            groups = [ data_group_assoc.group for data_group_assoc in dataset.groups ]
            for group in groups:
                if priority_access_group is None or priority_access_group.priority < group.priority:
                    priority_access_group = group
            if access_roles is None:
                access_roles = set( roles )
                access_groups = set( groups )
            else:
                access_roles.intersection_update( set( roles ) )
                access_groups.intersection_update( set( groups ) )
        
        #complete lists for output dataset access
        if access_roles:
            access_roles = list( access_roles )
        else:
            access_roles = []
        if access_groups:
            access_groups = list( access_groups)
        else:
            access_groups = []
        #if we have no roles or groups left after intersection,
        #take the highest priority group or role
        if not access_roles and not access_groups:
            if priority_access_role and priority_access_group:
                if priority_access_group.priority == priority_access_role.priority:
                    access_groups = [ priority_access_group ]
                    access_roles = [ priority_access_role ]
                elif priority_access_group.priority > priority_access_role.priority:
                    access_groups = [ priority_access_group ]
                else:
                   access_roles = [ priority_access_role ]
            elif priority_access_role:
                 access_roles = [ priority_access_role ]
            elif priority_access_group:
                access_groups = [ priority_access_group ]
        
        return access_groups, access_roles
    def add_group( self, group ):
        return group.add_dataset( self )
    def add_role( self, role ):
        return role.add_dataset( self )
    
    def has_group( self, group ):
        return bool( GroupDatasetAssociation.get_by( group_id = group.id, dataset_id = self.id  )  )
    def has_role( self, role ):
        return bool( RoleDatasetAssociation.get_by( role_id = role.id, dataset_id = self.id  )  )

    # FIXME: sqlalchemy will replace this
    def _delete(self):
        """Remove the file that corresponds to this data"""
        try:
            os.remove(self.data.file_name)
        except OSError, e:
            log.critical('%s delete error %s' % (self.__class__.__name__, e))



class HistoryDatasetAssociation( object ):
    states = Dataset.states
    access_actions = Dataset.access_actions
    def __init__( self, id=None, hid=None, name=None, info=None, blurb=None, peek=None, extension=None, 
                  dbkey=None, metadata=None, history=None, dataset=None, deleted=False, designation=None,
                  parent_id=None, validation_errors=None, visible=True, create_dataset = False, access_groups = [], access_roles = [] ):
        self.name = name or "Unnamed dataset"
        self.id = id
        self.hid = hid
        self.info = info
        self.blurb = blurb
        self.peek = peek
        self.extension = extension
        self.dbkey = dbkey
        self.designation = designation
        self._metadata = metadata or dict()
        self.deleted = deleted
        self.visible = visible
        # Relationships
        self.history = history
        if not dataset and create_dataset:
            dataset = Dataset( access_groups = access_groups, access_roles = access_roles )
            dataset.flush()
        self.dataset = dataset
        self.parent_id = parent_id
        self.validation_errors = validation_errors
    
    @property
    def ext( self ):
        return self.extension
    
    def get_dataset_state( self ):
        return self.dataset.state
    def set_dataset_state ( self, state ):
        self.dataset.state = state
        self.dataset.flush() #flush here, because hda.flush() won't flush the Dataset object
    state = property( get_dataset_state, set_dataset_state )
    
    def get_file_name( self ):
        return self.dataset.get_file_name()
            
    def set_file_name (self, filename):
        return self.dataset.set_file_name( filename )
        
    file_name = property( get_file_name, set_file_name )
    
    @property
    def extra_files_path( self ):
        return self.dataset.extra_files_path
    
    @property
    def datatype( self ):
        return datatypes_registry.get_datatype_by_extension( self.extension )

    def get_metadata( self ):
        if not self._metadata:
            self._metadata = dict()
        return MetadataCollection( self, self.datatype.metadata_spec )
    def set_metadata( self, bunch ):
        # Needs to accept a MetadataCollection, a bunch, or a dict
        self._metadata = dict( bunch.items() )
    metadata = property( get_metadata, set_metadata )

    """
    This provide backwards compatibility with using the old dbkey
    field in the database.  That field now maps to "old_dbkey" (see mapping.py).
    """
    def get_dbkey( self ):
        dbkey = self.metadata.dbkey
        if not isinstance(dbkey, list): dbkey = [dbkey]
        #if dbkey in [["?"], [None], []]: dbkey = [self.old_dbkey]
        if dbkey in [[None], []]: return "?"
        return dbkey[0]
    def set_dbkey( self, value ):
        if "dbkey" in self.datatype.metadata_spec:
            if not isinstance(value, list): 
                self.metadata.dbkey = [value]
            else: 
                self.metadata.dbkey = value
        #if isinstance(value, list): 
        #    self.old_dbkey = value[0]
        #else:
        #    self.old_dbkey = value
    dbkey = property( get_dbkey, set_dbkey )

    def change_datatype( self, new_ext ):
        self.clear_associated_files()
        datatypes_registry.change_datatype( self, new_ext )
    def get_size( self ):
        """Returns the size of the data on disk"""
        return self.dataset.get_size()
    def set_size( self ):
        """Returns the size of the data on disk"""
        return self.dataset.set_size()
    def has_data( self ):
        """Detects whether there is any data"""
        return self.dataset.has_data()
    def get_raw_data( self ):
        """Returns the full data. To stream it open the file_name and read/write as needed"""
        return self.datatype.get_raw_data( self )
    def write_from_stream( self, stream ):
        """Writes data from a stream"""
        self.datatype.write_from_stream(self, stream)
    def set_raw_data( self, data ):
        """Saves the data on the disc"""
        self.datatype.set_raw_data(self, data)
    def get_mime( self ):
        """Returns the mime type of the data"""
        return datatypes_registry.get_mimetype_by_extension( self.extension.lower() )
    def set_peek( self ):
        return self.datatype.set_peek( self )
    def init_meta( self, copy_from=None ):
        return self.datatype.init_meta( self, copy_from=copy_from )
    def set_meta( self, **kwd ):
        self.clear_associated_files( metadata_safe = True )
        return self.datatype.set_meta( self, **kwd )
    def set_readonly_meta( self, **kwd ):
        return self.datatype.set_readonly_meta( self, **kwd )
    def missing_meta( self ):
        return self.datatype.missing_meta( self )
    def as_display_type( self, type, **kwd ):
        return self.datatype.as_display_type( self, type, **kwd )
    def display_peek( self ):
        return self.datatype.display_peek( self )
    def display_name( self ):
        return self.datatype.display_name( self )
    def display_info( self ):
        return self.datatype.display_info( self )
    def get_converted_files_by_type( self, file_type ):
        valid = []
        for assoc in self.implicitly_converted_datasets:
            if not assoc.deleted and assoc.type == file_type:
                valid.append( assoc.dataset )
        return valid
    def clear_associated_files( self, metadata_safe = False, purge = False ):
        #metadata_safe = True means to only clear when assoc.metadata_safe == False
        for assoc in self.implicitly_converted_datasets:
            if not metadata_safe or not assoc.metadata_safe:
                assoc.clear( purge = purge )
    def get_child_by_designation(self, designation):
        for child in self.children:
            if child.designation == designation:
                return child
        return None

    def get_converter_types(self):
        return self.datatype.get_converter_types( self, datatypes_registry)
    
    def copy( self, copy_children = False, parent_id = None, target_user = None ):
        if target_user is None: target_user = self.user
        des = HistoryDatasetAssociation( hid=self.hid, name=self.name, info=self.info, blurb=self.blurb, peek=self.peek, extension=self.extension, dbkey=self.dbkey, metadata=self._metadata, dataset = self.dataset, visible=self.visible, deleted=self.deleted, parent_id=parent_id )
        des.flush()
        if copy_children:
            for child in self.children:
                child_copy = child.copy( copy_children = copy_children, parent_id = des.id )
        des.set_peek() #in some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
        des.flush()
        return des

    def add_validation_error( self, validation_error ):
        self.validation_errors.append( validation_error )

    def extend_validation_errors( self, validation_errors ):
        self.validation_errors.extend(validation_errors)

    def mark_deleted( self, include_children=True ):
        self.deleted = True
        if include_children:
            for child in self.children:
                child.mark_deleted()

    def allow_action( self, user, action ):
        return self.dataset.allow_action( user, action )


class History( object ):
    def __init__( self, id=None, name=None, user=None, default_roles = [], default_groups = [] ):
        self.id = id
        self.name = name or "Unnamed history"
        self.deleted = False
        self.purged = False
        self.genome_build = None
        # Relationships
        self.user = user
        self.datasets = []
        self.galaxy_sessions = []
        
        if not default_roles:
            if user:
                default_roles = user.default_roles
        if not default_groups:
            if user:
                default_groups = user.default_groups
            else:
                default_groups = [ GalaxyGroup.get( GalaxyGroup.public_id ) ]
        
        
        self.set_default_access( roles = default_roles, groups = default_groups )
        
    def _next_hid( self ):
        # TODO: override this with something in the database that ensures 
        # better integrity
        if len( self.datasets ) == 0:
            return 1
        else:
            last_hid = 0
            for dataset in self.datasets:
                if dataset.hid > last_hid:
                    last_hid = dataset.hid
            return last_hid + 1

    def add_galaxy_session( self, galaxy_session, association=None ):
        if association is None:
            self.galaxy_sessions.append( GalaxySessionToHistoryAssociation( galaxy_session, self ) )
        else:
            self.galaxy_sessions.append( association )

    def add_dataset( self, dataset, parent_id=None, genome_build=None, set_hid = True ):
        if isinstance( dataset, Dataset ):
            dataset = HistoryDatasetAssociation( dataset = dataset )
            dataset.flush()
        elif not isinstance( dataset, HistoryDatasetAssociation ):
            raise TypeError, "You can only add Dataset and HistoryDatasetAssociation instances to a history."
        if parent_id:
            for data in self.datasets:
                if data.id == parent_id:
                    dataset.hid = data.hid
                    break
            else:
                if set_hid: dataset.hid = self._next_hid()
        else:
            if set_hid: dataset.hid = self._next_hid()
        dataset.history = self
        if genome_build not in [None, '?']:
            self.genome_build = genome_build
        self.datasets.append( dataset )

    def copy( self, target_user = None ):
        if not target_user:
            target_user = self.user
        des = History( user = target_user )
        des.flush()
        des.name = self.name
        for data in self.datasets:
            new_data = data.copy( copy_children = True, target_user = target_user )
            des.add_dataset( new_data )
            new_data.flush()
        des.hid_counter = self.hid_counter
        des.flush()
        return des
    
    def set_default_access( self, groups = None, roles = None, dataset = False ):
        if groups is not None:
            for assoc in self.default_groups: #this is the association not the actual group
                assoc.delete()
                assoc.flush()
            for group in groups:
                assoc = DefaultHistoryGroupAssociation( self, group )
                assoc.flush()
        if roles is not None:
            for assoc in self.default_roles: #this is the association not the actual group
                assoc.delete()
                assoc.flush()
            for role in roles:
                assoc = DefaultHistoryRoleAssociation( self, role )
                assoc.flush()
        if dataset:
            for data in self.datasets:
                for hda in data.dataset.history_associations:
                    if self.user and hda.history not in self.user.histories:
                        break
                else:
                    if groups is not None:
                        for assoc in data.dataset.groups: #this is the association not the actual group
                            assoc.delete()
                            assoc.flush()
                        for group in groups:
                            group.add_dataset( data )
                    if roles is not None:
                        for assoc in data.dataset.roles: #this is the association not the actual group
                            assoc.delete()
                            assoc.flush()
                        for role in roles:
                            role.add_dataset( data )



# class Query( object ):
#     def __init__( self, name=None, state=None, tool_parameters=None, history=None ):
#         self.name = name or "Unnamed query"
#         self.state = state
#         self.tool_parameters = tool_parameters
#         # Relationships
#         self.history = history
#         self.datasets = []

class Old_Dataset( Dataset ):
    pass
            
class ValidationError( object ):
    def __init__( self, message=None, err_type=None, attributes=None ):
        self.message = message
        self.err_type = err_type
        self.attributes = attributes

class DatasetToValidationErrorAssociation( object ):
    def __init__( self, dataset, validation_error ):
        self.dataset = dataset
        self.validation_error = validation_error

class ImplicitlyConvertedDatasetAssociation( object ):
    def __init__( self, id = None, parent = None, dataset = None, file_type = None, deleted = False, purged = False, metadata_safe = True ):
        self.id = id
        self.dataset = dataset
        self.parent = parent
        self.type = file_type
        self.deleted = deleted
        self.purged = purged
        self.metadata_safe = metadata_safe

    def clear( self, purge = False ):
        self.deleted = True
        if self.dataset:
            self.dataset.deleted = True
            self.dataset.purged = purge
        if purge: #do something with purging
            self.purged = True
            try: os.unlink( self.file_name )
            except Exception, e: print "Failed to purge associated file (%s) from disk: %s" % ( self.file_name, e )

class Event( object ):
    def __init__( self, message=None, history=None, user=None, galaxy_session=None ):
        self.history = history
        self.galaxy_session = galaxy_session
        self.user = user
        self.tool_id = None
        self.message = message

class GalaxySession( object ):
    def __init__( self, id=None, user=None, remote_host=None, remote_addr=None, referer=None, current_history_id=None, session_key=None, is_valid=False, prev_session_id=None ):
        self.id = id
        self.user = user
        self.remote_host = remote_host
        self.remote_addr = remote_addr
        self.referer = referer
        self.current_history_id = current_history_id
        self.session_key = session_key
        self.is_valid = is_valid
        self.prev_session_id = prev_session_id
        self.histories = []

    def add_history( self, history, association=None ):
        if association is None:
            self.histories.append( GalaxySessionToHistoryAssociation( self, history ) )
        else:
            self.histories.append( association )
    
class GalaxySessionToHistoryAssociation( object ):
    def __init__( self, galaxy_session, history ):
        self.galaxy_session = galaxy_session
        self.history = history
        
class StoredWorkflow( object ):
    def __init__( self ):
        self.id = None
        self.user = None
        self.name = None
        self.latest_workflow_id = None
        self.workflows = []

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
        self.tool_id = None
        self.tool_inputs = None
        self.tool_errors = None
        self.position = None
        self.input_connections = None
        self.config = None
        
class WorkflowStepConnection( object ):
    def __init__( self ):
        self.output_step_id = None
        self.output_name = None
        self.input_step_id = None
        self.input_name = None
        
class StoredWorkflowUserShareAssociation( object ):
    def __init__( self ):
        self.stored_workflow = None
        self.user = None

class StoredWorkflowMenuEntry( object ):
    def __init__( self ):
        self.stored_workflow = None
        self.user = None
        self.order_index = None

## ---- Utility methods -------------------------------------------------------

def directory_hash_id( id ):
    s = str( id )
    l = len( s )
    # Shortcut -- ids 0-999 go under ../000/
    if l < 4:
        return [ "000" ]
    # Pad with zeros until a multiple of three
    padded = ( ( 3 - len( s ) % 3 ) * "0" ) + s
    # Drop the last three digits -- 1000 files per directory
    padded = padded[:-3]
    # Break into chunks of three
    return [ padded[i*3:(i+1)*3] for i in range( len( padded ) // 3 ) ]
