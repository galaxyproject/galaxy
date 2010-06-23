"""
Galaxy data model classes

Naming: try to use class names that have a distinct plural form so that
the relationship cardinalities are obvious (e.g. prefer Dataset to Data)
"""

import os.path, os, errno, sys, codecs, operator
import galaxy.datatypes
from galaxy.util.bunch import Bunch
from galaxy import util
import tempfile
import galaxy.datatypes.registry
from galaxy.datatypes.metadata import MetadataCollection
from galaxy.security import RBACAgent, get_permitted_actions
from galaxy.util.hash_util import *
from galaxy.web.form_builder import *
import logging
log = logging.getLogger( __name__ )
from sqlalchemy.orm import object_session
import pexpect

datatypes_registry = galaxy.datatypes.registry.Registry() #Default Value Required for unit tests

def set_datatypes_registry( d_registry ):
    """
    Set up datatypes_registry
    """
    global datatypes_registry
    datatypes_registry = d_registry

class User( object ):
    def __init__( self, email=None, password=None ):
        self.email = email
        self.password = password
        self.external = False
        self.deleted = False
        self.purged = False
        self.username = None
        # Relationships
        self.histories = []
        self.credentials = []
        
    def set_password_cleartext( self, cleartext ):
        """Set 'self.password' to the digest of 'cleartext'."""
        self.password = new_secure_hash( text_type=cleartext )
    def check_password( self, cleartext ):
        """Check if 'cleartext' matches 'self.password' when hashed."""
        return self.password == new_secure_hash( text_type=cleartext )
    def all_roles( self ):
        roles = [ ura.role for ura in self.roles ]
        for group in [ uga.group for uga in self.groups ]:
            for role in [ gra.role for gra in group.roles ]:
                if role not in roles:
                    roles.append( role )
        return roles
    def accessible_libraries(self, trans, actions):
        # get all permitted libraries for this user
        all_libraries = trans.sa_session.query( trans.app.model.Library ) \
                                        .filter( trans.app.model.Library.table.c.deleted == False ) \
                                        .order_by( trans.app.model.Library.name )
        roles = self.all_roles()
        actions_to_check = actions
        # The libraries dictionary looks like: { library : '1,2' }, library : '3' }
        # Its keys are the libraries that should be displayed for the current user and whose values are a
        # string of comma-separated folder ids, of the associated folders the should NOT be displayed.
        # The folders that should not be displayed may not be a complete list, but it is ultimately passed
        # to the calling method to keep from re-checking the same folders when the library / folder
        # select lists are rendered.
        libraries = {}
        for library in all_libraries:
            can_show, hidden_folder_ids = trans.app.security_agent.show_library_item( self, roles, library, actions_to_check )
            if can_show:
                libraries[ library ] = hidden_folder_ids
        return libraries
    def accessible_request_types(self, trans):
        # get all permitted libraries for this user
        all_rt_list = trans.sa_session.query( trans.app.model.RequestType ) \
                                      .filter( trans.app.model.RequestType.table.c.deleted == False ) \
                                      .order_by( trans.app.model.RequestType.name )
        roles = self.all_roles()
        rt_list = []
        for rt in all_rt_list:
            for permission in rt.actions:
                if permission.role.id in [r.id for r in roles]:
                   rt_list.append(rt) 
        return list(set(rt_list))
    
class Job( object ):
    """
    A job represents a request to run a tool given input datasets, tool 
    parameters, and output datasets.
    """
    states = Bunch( NEW = 'new',
                    UPLOAD = 'upload',
                    WAITING = 'waiting',
                    QUEUED = 'queued',
                    RUNNING = 'running',
                    OK = 'ok',
                    ERROR = 'error',
                    DELETED = 'deleted' )
    def __init__( self ):
        self.session_id = None
        self.user_id = None
        self.tool_id = None
        self.tool_version = None
        self.command_line = None
        self.param_filename = None
        self.parameters = []
        self.input_datasets = []
        self.output_datasets = []
        self.output_library_datasets = []
        self.state = Job.states.NEW
        self.info = None
        self.job_runner_name = None
        self.job_runner_external_id = None
        self.post_job_actions = None
        
    def add_parameter( self, name, value ):
        self.parameters.append( JobParameter( name, value ) )
    def add_input_dataset( self, name, dataset ):
        self.input_datasets.append( JobToInputDatasetAssociation( name, dataset ) )
    def add_output_dataset( self, name, dataset ):
        self.output_datasets.append( JobToOutputDatasetAssociation( name, dataset ) )
    def add_output_library_dataset( self, name, dataset ):
        self.output_library_datasets.append( JobToOutputLibraryDatasetAssociation( name, dataset ) )
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
    def check_if_output_datasets_deleted( self ):
        """
        Return true if all of the output datasets associated with this job are
        in the deleted state
        """
        for dataset_assoc in self.output_datasets:
            dataset = dataset_assoc.dataset
            # only the originator of the job can delete a dataset to cause
            # cancellation of the job, no need to loop through history_associations
            if not dataset.deleted:
                return False
        return True
    def mark_deleted( self ):
        """
        Mark this job as deleted, and mark any output datasets as discarded.
        """
        self.state = Job.states.DELETED
        self.info = "Job output deleted by user before job completed."
        for dataset_assoc in self.output_datasets:
            dataset = dataset_assoc.dataset
            dataset.deleted = True
            dataset.state = dataset.states.DISCARDED
            for dataset in dataset.dataset.history_associations:
                # propagate info across shared datasets
                dataset.deleted = True
                dataset.blurb = 'deleted'
                dataset.peek = 'Job deleted'
                dataset.info = 'Job output deleted by user before job completed'

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

class JobToOutputLibraryDatasetAssociation( object ):
    def __init__( self, name, dataset ):
        self.name = name
        self.dataset = dataset

class PostJobAction( object ):
    def __init__( self, action_type, workflow_step, output_name = None, action_arguments = None):
        self.action_type = action_type
        self.output_name = output_name
        self.action_arguments = action_arguments
        self.workflow_step = workflow_step

class JobExternalOutputMetadata( object ):
    def __init__( self, job = None, dataset = None ):
        self.job = job
        if isinstance( dataset, galaxy.model.HistoryDatasetAssociation ):
            self.history_dataset_association = dataset
        elif isinstance( dataset, galaxy.model.LibraryDatasetDatasetAssociation ):
            self.library_dataset_dataset_association = dataset
    @property
    def dataset( self ):
        if self.history_dataset_association:
            return self.history_dataset_association
        elif self.library_dataset_dataset_association:
            return self.library_dataset_dataset_association
        return None

class Group( object ):
    def __init__( self, name = None ):
        self.name = name
        self.deleted = False

class UserGroupAssociation( object ):
    def __init__( self, user, group ):
        self.user = user
        self.group = group

class History( object ):
    def __init__( self, id=None, name=None, user=None ):
        self.id = id
        self.name = name or "Unnamed history"
        self.deleted = False
        self.purged = False
        self.genome_build = None
        self.published = False
        # Relationships
        self.user = user
        self.datasets = []
        self.galaxy_sessions = []
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
            dataset = HistoryDatasetAssociation( dataset = dataset, copied_from = dataset )
            object_session( self ).add( dataset )
            object_session( self ).flush()
        elif not isinstance( dataset, HistoryDatasetAssociation ):
            raise TypeError, "You can only add Dataset and HistoryDatasetAssociation instances to a history ( you tried to add %s )." % str( dataset )
        if parent_id:
            for data in self.datasets:
                if data.id == parent_id:
                    dataset.hid = data.hid
                    break
            else:
                if set_hid:
                    dataset.hid = self._next_hid()
        else:
            if set_hid:
                dataset.hid = self._next_hid()
        dataset.history = self
        if genome_build not in [None, '?']:
            self.genome_build = genome_build
        self.datasets.append( dataset )
    def copy( self, name=None, target_user=None, activatable=False ):
        if not name:
            name = self.name
        if not target_user:
            target_user = self.user
        new_history = History( name=name, user=target_user )
        object_session( self ).add( new_history )
        object_session( self ).flush()
        if activatable:
            hdas = self.activatable_datasets
        else:
            hdas = self.active_datasets
        for hda in hdas:
            new_hda = hda.copy( copy_children=True, target_history=new_history )
            new_history.add_dataset( new_hda, set_hid = False )
            object_session( self ).add( new_hda )
            object_session( self ).flush()
        new_history.hid_counter = self.hid_counter
        object_session( self ).add( new_history )
        object_session( self ).flush()
        return new_history
    @property
    def activatable_datasets( self ):
        # This needs to be a list
        return [ hda for hda in self.datasets if not hda.dataset.deleted ]
    def get_display_name( self ):
        """ History name can be either a string or a unicode object. If string, convert to unicode object assuming 'utf-8' format. """
        history_name = self.name
        if isinstance(history_name, str):
            history_name = unicode(history_name, 'utf-8')
        return history_name

class HistoryUserShareAssociation( object ):
    def __init__( self ):
        self.history = None
        self.user = None

class UserRoleAssociation( object ):
    def __init__( self, user, role ):
        self.user = user
        self.role = role

class GroupRoleAssociation( object ):
    def __init__( self, group, role ):
        self.group = group
        self.role = role

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

class DatasetPermissions( object ):
    def __init__( self, action, dataset, role ):
        self.action = action
        self.dataset = dataset
        self.role = role

class LibraryPermissions( object ):
    def __init__( self, action, library_item, role ):
        self.action = action
        if isinstance( library_item, Library ):
            self.library = library_item
        else:
            raise "Invalid Library specified: %s" % library_item.__class__.__name__
        self.role = role

class LibraryFolderPermissions( object ):
    def __init__( self, action, library_item, role ):
        self.action = action
        if isinstance( library_item, LibraryFolder ):
            self.folder = library_item
        else:
            raise "Invalid LibraryFolder specified: %s" % library_item.__class__.__name__
        self.role = role

class LibraryDatasetPermissions( object ):
    def __init__( self, action, library_item, role ):
        self.action = action
        if isinstance( library_item, LibraryDataset ):
            self.library_dataset = library_item
        else:
            raise "Invalid LibraryDataset specified: %s" % library_item.__class__.__name__
        self.role = role

class LibraryDatasetDatasetAssociationPermissions( object ):
    def __init__( self, action, library_item, role ):
        self.action = action
        if isinstance( library_item, LibraryDatasetDatasetAssociation ):
            self.library_dataset_dataset_association = library_item
        else:
            raise "Invalid LibraryDatasetDatasetAssociation specified: %s" % library_item.__class__.__name__
        self.role = role

class DefaultUserPermissions( object ):
    def __init__( self, user, action, role ):
        self.user = user
        self.action = action
        self.role = role

class DefaultHistoryPermissions( object ):
    def __init__( self, history, action, role ):
        self.history = history
        self.action = action
        self.role = role

class Dataset( object ):
    states = Bunch( NEW = 'new',
                    UPLOAD = 'upload',
                    QUEUED = 'queued',
                    RUNNING = 'running',
                    OK = 'ok',
                    EMPTY = 'empty',
                    ERROR = 'error',
                    DISCARDED = 'discarded',
                    SETTING_METADATA = 'setting_metadata' )
    permitted_actions = get_permitted_actions( filter='DATASET' )
    file_path = "/tmp/"
    engine = None
    def __init__( self, id=None, state=None, external_filename=None, extra_files_path=None, file_size=None, purgable=True ):
        self.id = id
        self.state = state
        self.deleted = False
        self.purged = False
        self.purgable = purgable
        self.external_filename = external_filename
        self._extra_files_path = extra_files_path
        self.file_size = file_size
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
                if not os.path.exists( dir ):
                    os.makedirs( dir )
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
    def get_size( self, nice_size=False ):
        """Returns the size of the data on disk"""
        if self.file_size:
            if nice_size:
                return galaxy.datatypes.data.nice_size( self.file_size )
            else:
                return self.file_size
        else:
            try:
                if nice_size:
                    return galaxy.datatypes.data.nice_size( os.path.getsize( self.file_name ) )
                else:
                    return os.path.getsize( self.file_name )
            except OSError:
                return 0
    def set_size( self ):
        """Returns the size of the data on disk"""
        try:
            if not self.file_size:
                self.file_size = os.path.getsize( self.file_name )
        except OSError:
            self.file_size = 0
    def has_data( self ):
        """Detects whether there is any data"""
        return self.get_size() > 0
    def mark_deleted( self, include_children=True ):
        self.deleted = True
    def is_multi_byte( self ):
        if not self.has_data():
            return False
        try:
            return util.is_multi_byte( codecs.open( self.file_name, 'r', 'utf-8' ).read( 100 ) )
        except UnicodeDecodeError, e:
            return False
    # FIXME: sqlalchemy will replace this
    def _delete(self):
        """Remove the file that corresponds to this data"""
        try:
            os.remove(self.data.file_name)
        except OSError, e:
            log.critical('%s delete error %s' % (self.__class__.__name__, e))
    def get_access_roles( self, trans ):
        roles = []
        for dp in self.actions:
            if dp.action == trans.app.security_agent.permitted_actions.DATASET_ACCESS.action:
                roles.append( dp.role )
        return roles

class DatasetInstance( object ):
    """A base class for all 'dataset instances', HDAs, LDAs, etc"""
    states = Dataset.states
    permitted_actions = Dataset.permitted_actions
    def __init__( self, id=None, hid=None, name=None, info=None, blurb=None, peek=None, extension=None, 
                  dbkey=None, metadata=None, history=None, dataset=None, deleted=False, designation=None,
                  parent_id=None, validation_errors=None, visible=True, create_dataset=False, sa_session=None ):
        self.name = name or "Unnamed dataset"
        self.id = id
        self.info = info
        self.blurb = blurb
        self.peek = peek
        self.extension = extension
        self.designation = designation
        self.metadata = metadata or dict()
        if dbkey: #dbkey is stored in metadata, only set if non-zero, or else we could clobber one supplied by input 'metadata'
            self.dbkey = dbkey
        self.deleted = deleted
        self.visible = visible
        # Relationships
        if not dataset and create_dataset:
            # Had to pass the sqlalchemy session in order to create a new dataset
            dataset = Dataset( state=Dataset.states.NEW )
            sa_session.add( dataset )
            sa_session.flush()
        self.dataset = dataset
        self.parent_id = parent_id
        self.validation_errors = validation_errors
    @property
    def ext( self ):
        return self.extension
    def get_dataset_state( self ):
        #self._state is currently only used when setting metadata externally
        #leave setting the state as-is, we'll currently handle this specially in the external metadata code
        if self._state:
            return self._state
        return self.dataset.state
    def set_dataset_state ( self, state ):
        self.dataset.state = state
        object_session( self ).add( self.dataset )
        object_session( self ).flush() #flush here, because hda.flush() won't flush the Dataset object
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
        if not hasattr( self, '_metadata_collection' ) or self._metadata_collection.parent != self: #using weakref to store parent (to prevent circ ref), does a Session.clear() cause parent to be invalidated, while still copying over this non-database attribute?
            self._metadata_collection = MetadataCollection( self )
        return self._metadata_collection
    def set_metadata( self, bunch ):
        # Needs to accept a MetadataCollection, a bunch, or a dict
        self._metadata = self.metadata.make_dict_copy( bunch )
    metadata = property( get_metadata, set_metadata )
    # This provide backwards compatibility with using the old dbkey
    # field in the database.  That field now maps to "old_dbkey" (see mapping.py).
    def get_dbkey( self ):
        dbkey = self.metadata.dbkey
        if not isinstance(dbkey, list): dbkey = [dbkey]
        if dbkey in [[None], []]: return "?"
        return dbkey[0]
    def set_dbkey( self, value ):
        if "dbkey" in self.datatype.metadata_spec:
            if not isinstance(value, list): 
                self.metadata.dbkey = [value]
            else: 
                self.metadata.dbkey = value
    dbkey = property( get_dbkey, set_dbkey )
    def change_datatype( self, new_ext ):
        self.clear_associated_files()
        datatypes_registry.change_datatype( self, new_ext )
    def get_size( self, nice_size=False ):
        """Returns the size of the data on disk"""
        if nice_size:
            return galaxy.datatypes.data.nice_size( self.dataset.get_size() )
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
    def is_multi_byte( self ):
        """Data consists of multi-byte characters"""
        return self.dataset.is_multi_byte()
    def set_peek( self, is_multi_byte=False ):
        return self.datatype.set_peek( self, is_multi_byte=is_multi_byte )
    def init_meta( self, copy_from=None ):
        return self.datatype.init_meta( self, copy_from=copy_from )
    def set_meta( self, **kwd ):
        self.clear_associated_files( metadata_safe = True )
        return self.datatype.set_meta( self, **kwd )
    def missing_meta( self, **kwd ):
        return self.datatype.missing_meta( self, **kwd )
    def as_display_type( self, type, **kwd ):
        return self.datatype.as_display_type( self, type, **kwd )
    def display_peek( self ):
        return self.datatype.display_peek( self )
    def display_name( self ):
        return self.datatype.display_name( self )
    def display_info( self ):
        return self.datatype.display_info( self )
    def get_converted_files_by_type( self, file_type ):
        for assoc in self.implicitly_converted_datasets:
            if not assoc.deleted and assoc.type == file_type:
                return assoc.dataset
        return None
    def get_converted_dataset(self, trans, target_ext):
        """
        Return converted dataset(s) if they exist. If not converted yet, do so and return None (the first time).
        If unconvertible, raise exception.
        """
        # See if we can convert the dataset
        if target_ext not in self.get_converter_types():
            raise ValueError("Conversion from '%s' to '%s' not possible", self.extension, target_ext)
        
        # See if converted dataset already exists
        converted_dataset = self.get_converted_files_by_type( target_ext )
        if converted_dataset:
            return converted_dataset
        
        # Conversion is possible but hasn't been done yet, run converter.
        # Check if we have dependencies
        deps = {}
        try:
            fail_dependencies = False
            depends_on = trans.app.datatypes_registry.converter_deps[self.extension][target_ext]
            for dependency in depends_on:
                dep_dataset = self.get_converted_dataset(trans, dependency)
                if dep_dataset is None or dep_dataset.state != trans.app.model.Job.states.OK:
                    fail_dependencies = True
                else:
                    deps[dependency] = dep_dataset
            if fail_dependencies:
                return None
        except ValueError:
            raise ValueError("A dependency could not be converted.")
        except KeyError:
            pass # No deps
            
        assoc = ImplicitlyConvertedDatasetAssociation( parent=self, file_type=target_ext, metadata_safe=False )
        new_dataset = self.datatype.convert_dataset( trans, self, target_ext, return_output=True, visible=False, deps=deps ).values()[0]
        new_dataset.hid = self.hid
        new_dataset.name = self.name
        trans.sa_session.add( new_dataset )
        trans.sa_session.flush()
        assoc.dataset = new_dataset
        trans.sa_session.add( assoc )
        trans.sa_session.flush()
        return None
    def clear_associated_files( self, metadata_safe = False, purge = False ):
        raise 'Unimplemented'
    def get_child_by_designation(self, designation):
        for child in self.children:
            if child.designation == designation:
                return child
        return None
    def get_converter_types(self):
        return self.datatype.get_converter_types( self, datatypes_registry )
    def find_conversion_destination( self, accepted_formats, **kwd ):
        """Returns ( target_ext, existing converted dataset )"""
        return self.datatype.find_conversion_destination( self, accepted_formats, datatypes_registry, **kwd )
    def add_validation_error( self, validation_error ):
        self.validation_errors.append( validation_error )
    def extend_validation_errors( self, validation_errors ):
        self.validation_errors.extend(validation_errors)
    def mark_deleted( self, include_children=True ):
        self.deleted = True
        if include_children:
            for child in self.children:
                child.mark_deleted()
    def mark_undeleted( self, include_children=True ):
        self.deleted = False
        if include_children:
            for child in self.children:
                child.mark_undeleted()
    def undeletable( self ):
        if self.purged:
            return False
        return True
    @property
    def is_pending( self ):
        """
        Return true if the dataset is neither ready nor in error
        """
        return self.state in ( self.states.NEW, self.states.UPLOAD,
                               self.states.QUEUED, self.states.RUNNING,
                               self.states.SETTING_METADATA )
    @property
    def source_library_dataset( self ):
        def get_source( dataset ):
            if isinstance( dataset, LibraryDatasetDatasetAssociation ):
                if dataset.library_dataset:
                    return ( dataset, dataset.library_dataset )
            if dataset.copied_from_library_dataset_dataset_association:
                source = get_source( dataset.copied_from_library_dataset_dataset_association )
                if source:
                    return source
            if dataset.copied_from_history_dataset_association:
                source = get_source( dataset.copied_from_history_dataset_association )
                if source:
                    return source
            return ( None, None )
        return get_source( self )

    def get_display_applications( self, trans ):
        return self.datatype.get_display_applications_by_dataset( self, trans )

class HistoryDatasetAssociation( DatasetInstance ):
    def __init__( self, 
                  hid = None, 
                  history = None, 
                  copied_from_history_dataset_association = None, 
                  copied_from_library_dataset_dataset_association = None, 
                  sa_session = None,
                  **kwd ):
        # FIXME: sa_session is must be passed to DataSetInstance if the create_dataset 
        # parameter is True so that the new object can be flushed.  Is there a better way?
        DatasetInstance.__init__( self, sa_session=sa_session, **kwd )
        self.hid = hid
        # Relationships
        self.history = history
        self.copied_from_history_dataset_association = copied_from_history_dataset_association
        self.copied_from_library_dataset_dataset_association = copied_from_library_dataset_dataset_association
    def copy( self, copy_children = False, parent_id = None, target_history = None ):
        hda = HistoryDatasetAssociation( hid=self.hid, 
                                         name=self.name, 
                                         info=self.info, 
                                         blurb=self.blurb, 
                                         peek=self.peek, 
                                         extension=self.extension, 
                                         dbkey=self.dbkey, 
                                         dataset = self.dataset, 
                                         visible=self.visible, 
                                         deleted=self.deleted, 
                                         parent_id=parent_id, 
                                         copied_from_history_dataset_association=self,
                                         history = target_history )
        object_session( self ).add( hda )
        object_session( self ).flush()
        hda.set_size()
        # Need to set after flushed, as MetadataFiles require dataset.id
        hda.metadata = self.metadata
        if copy_children:
            for child in self.children:
                child_copy = child.copy( copy_children = copy_children, parent_id = hda.id )
        if not self.datatype.copy_safe_peek:
            # In some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
            hda.set_peek()
        object_session( self ).flush()
        return hda
    def to_library_dataset_dataset_association( self, target_folder, replace_dataset=None, parent_id=None, user=None ):
        if replace_dataset:
            # The replace_dataset param ( when not None ) refers to a LibraryDataset that is being replaced with a new version.
            library_dataset = replace_dataset
        else:
            # If replace_dataset is None, the Library level permissions will be taken from the folder and applied to the new 
            # LibraryDataset, and the current user's DefaultUserPermissions will be applied to the associated Dataset.
            library_dataset = LibraryDataset( folder=target_folder, name=self.name, info=self.info )
            object_session( self ).add( library_dataset )
            object_session( self ).flush()
        if not user:
            user = self.history.user
        ldda = LibraryDatasetDatasetAssociation( name=self.name, 
                                                 info=self.info,
                                                 blurb=self.blurb, 
                                                 peek=self.peek, 
                                                 extension=self.extension, 
                                                 dbkey=self.dbkey, 
                                                 dataset=self.dataset, 
                                                 library_dataset=library_dataset,
                                                 visible=self.visible, 
                                                 deleted=self.deleted, 
                                                 parent_id=parent_id,
                                                 copied_from_history_dataset_association=self,
                                                 user=user )
        object_session( self ).add( ldda )
        object_session( self ).flush()
        # Permissions must be the same on the LibraryDatasetDatasetAssociation and the associated LibraryDataset
        # Must set metadata after ldda flushed, as MetadataFiles require ldda.id
        ldda.metadata = self.metadata
        if not replace_dataset:
            target_folder.add_library_dataset( library_dataset, genome_build=ldda.dbkey )
            object_session( self ).add( target_folder )
            object_session( self ).flush()
        library_dataset.library_dataset_dataset_association_id = ldda.id
        object_session( self ).add( library_dataset )
        object_session( self ).flush()
        for child in self.children:
            child_copy = child.to_library_dataset_dataset_association( target_folder=target_folder,
                                                                       replace_dataset=replace_dataset,
                                                                       parent_id=ldda.id,
                                                                       user=ldda.user )
        if not self.datatype.copy_safe_peek:
            # In some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
            ldda.set_peek()
        object_session( self ).flush()
        return ldda
    def clear_associated_files( self, metadata_safe = False, purge = False ):
        # metadata_safe = True means to only clear when assoc.metadata_safe == False
        for assoc in self.implicitly_converted_datasets:
            if not metadata_safe or not assoc.metadata_safe:
                assoc.clear( purge = purge )
    def get_display_name( self ):
        ## Name can be either a string or a unicode object. If string, convert to unicode object assuming 'utf-8' format.
        hda_name = self.name
        if isinstance(hda_name, str):
            hda_name = unicode(hda_name, 'utf-8')
        return hda_name
    def get_access_roles( self, trans ):
        return self.dataset.get_access_roles( trans )

class HistoryDatasetAssociationDisplayAtAuthorization( object ):
    def __init__( self, hda=None, user=None, site=None ):
        self.history_dataset_association = hda
        self.user = user
        self.site = site

class Library( object ):
    permitted_actions = get_permitted_actions( filter='LIBRARY' )
    api_collection_visible_keys = ( 'id', 'name' )
    api_element_visible_keys = ( 'name', 'description', 'synopsis' )
    def __init__( self, name=None, description=None, synopsis=None, root_folder=None ):
        self.name = name or "Unnamed library"
        self.description = description
        self.synopsis = synopsis
        self.root_folder = root_folder
    def get_info_association( self, restrict=False, inherited=False ):
        if self.info_association:
            if not inherited or self.info_association[0].inheritable:
                return self.info_association[0], inherited
            else:
                return None, inherited
        return None, inherited
    def get_template_widgets( self, trans, get_contents=True ):
        # See if we have any associated templates - the returned value for
        # inherited is not applicable at the library level.  The get_contents
        # param is passed by callers that are inheriting a template - these
        # are usually new library datsets for which we want to include template
        # fields on the upload form, but not the contents of the inherited template.
        info_association, inherited = self.get_info_association()
        if info_association:
            template = info_association.template
            if get_contents:
                # See if we have any field contents
                info = info_association.info
                if info:
                    return template.get_widgets( trans.user, contents=info.content )
            return template.get_widgets( trans.user )
        return []
    def get_access_roles( self, trans ):
        roles = []
        for lp in self.actions:
            if lp.action == trans.app.security_agent.permitted_actions.LIBRARY_ACCESS.action:
                roles.append( lp.role )
        return roles
    def get_display_name( self ):
        # Library name can be either a string or a unicode object. If string, 
        # convert to unicode object assuming 'utf-8' format.
        name = self.name
        if isinstance( name, str ):
            name = unicode( name, 'utf-8' )
        return name
    def get_api_value( self, view='collection' ):
        rval = {}
        try:
            visible_keys = self.__getattribute__( 'api_' + view + '_visible_keys' )
        except AttributeError:
            raise Exception( 'Unknown API view: %s' % view )
        for key in visible_keys:
            try:
                rval[key] = self.__getattribute__( key )
            except AttributeError:
                rval[key] = None
        return rval

class LibraryFolder( object ):
    api_element_visible_keys = ( 'name', 'description', 'item_count', 'genome_build' )
    def __init__( self, name=None, description=None, item_count=0, order_id=None ):
        self.name = name or "Unnamed folder"
        self.description = description
        self.item_count = item_count
        self.order_id = order_id
        self.genome_build = None
    def add_library_dataset( self, library_dataset, genome_build=None ):
        library_dataset.folder_id = self.id
        library_dataset.order_id = self.item_count
        self.item_count += 1
        if genome_build not in [None, '?']:
            self.genome_build = genome_build
    def add_folder( self, folder ):
        folder.parent_id = self.id
        folder.order_id = self.item_count
        self.item_count += 1
    def get_info_association( self, restrict=False, inherited=False ):
        # If restrict is True, we will return this folder's info_association, not inheriting.
        # If restrict is False, we'll return the next available info_association in the
        # inheritable hierarchy if it is "inheritable".  True is also returned if the
        # info_association was inherited and False if not.  This enables us to eliminate
        # displaying any contents of the inherited template.
        if self.info_association:
            if not inherited or self.info_association[0].inheritable:
                return self.info_association[0], inherited
            else:
                return None, inherited
        if restrict:
            return None, inherited
        if self.parent:
            return self.parent.get_info_association( inherited=True )
        if self.library_root:
            return self.library_root[0].get_info_association( inherited=True )
        return None, inherited
    def get_template_widgets( self, trans, get_contents=True ):
        # See if we have any associated templates.  The get_contents
        # param is passed by callers that are inheriting a template - these
        # are usually new library datsets for which we want to include template
        # fields on the upload form.
        info_association, inherited = self.get_info_association()
        if info_association:
            if inherited:
                template = info_association.template.current.latest_form
            else:
                template = info_association.template
            # See if we have any field contents, but only if the info_association was
            # not inherited ( we do not want to display the inherited contents ).
            if not inherited and get_contents:
                info = info_association.info
                if info:
                    return template.get_widgets( trans.user, info.content )
            else:
                return template.get_widgets( trans.user )
        return []
    @property
    def active_library_datasets( self ):
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
         # This needs to be a list
        active_library_datasets = [ ld for ld in self.datasets if not ld.library_dataset_dataset_association.deleted ]
        return sort_by_attr( [ ld for ld in active_library_datasets ], 'name' ) 
    @property
    def activatable_library_datasets( self ):
         # This needs to be a list
        return [ ld for ld in self.datasets if not ld.library_dataset_dataset_association.dataset.deleted ]
    @property
    def active_datasets( self ):
        # This needs to be a list
        return [ ld.library_dataset_dataset_association.dataset for ld in self.datasets if not ld.library_dataset_dataset_association.deleted ]
    def get_display_name( self ):
        # Library folder name can be either a string or a unicode object. If string, 
        # convert to unicode object assuming 'utf-8' format.
        name = self.name
        if isinstance( name, str ):
            name = unicode( name, 'utf-8' )
        return name
    def get_api_value( self, view='collection' ):
        rval = {}
        try:
            visible_keys = self.__getattribute__( 'api_' + view + '_visible_keys' )
        except AttributeError:
            raise Exception( 'Unknown API view: %s' % view )
        for key in visible_keys:
            try:
                rval[key] = self.__getattribute__( key )
            except AttributeError:
                rval[key] = None
        return rval
    @property
    def parent_library( self ):
        f = self
        while f.parent:
            f = f.parent
        return f.library_root[0]

class LibraryDataset( object ):
    # This class acts as a proxy to the currently selected LDDA
    def __init__( self, folder=None, order_id=None, name=None, info=None, library_dataset_dataset_association=None, **kwd ):
        self.folder = folder
        self.order_id = order_id
        self.name = name
        self.info = info
        self.library_dataset_dataset_association = library_dataset_dataset_association
    def set_library_dataset_dataset_association( self, ldda ):
        self.library_dataset_dataset_association = ldda
        ldda.library_dataset = self
        object_session( self ).add_all( ( ldda, self ) )
        object_session( self ).flush()
    def get_info( self ):
        if self.library_dataset_dataset_association:
            return self.library_dataset_dataset_association.info
        elif self._info:
            return self._info
        else:
            return 'no info'
    def set_info( self, info ):
        self._info = info
    info = property( get_info, set_info )
    def get_name( self ):
        if self.library_dataset_dataset_association:
            return self.library_dataset_dataset_association.name
        elif self._name:
            return self._name
        else:
            return 'Unnamed dataset'
    def set_name( self, name ):
        self._name = name
    name = property( get_name, set_name )
    def display_name( self ):
        self.library_dataset_dataset_association.display_name()
    def get_purged( self ):
        return self.library_dataset_dataset_association.dataset.purged
    def set_purged( self, purged ):
        if purged:
            raise Exception( "Not implemented" )
        if not purged and self.purged:
            raise Exception( "Cannot unpurge once purged" )
    purged = property( get_purged, set_purged )
    def get_api_value( self, view='collection' ):
        # Since this class is a proxy to rather complex attributes we want to
        # display in other objects, we can't use the simpler method used by
        # other model classes.
        ldda = self.library_dataset_dataset_association
        rval = dict( name = ldda.name,
                     uploaded_by = ldda.user.email,
                     message = ldda.message,
                     date_uploaded = ldda.create_time.isoformat(),
                     file_size = int( ldda.get_size() ),
                     data_type = ldda.ext,
                     genome_build = ldda.dbkey,
                     misc_info = ldda.info,
                     misc_blurb = ldda.blurb )
        for name, spec in ldda.metadata.spec.items():
            val = ldda.metadata.get( name )
            if isinstance( val, MetadataFile ):
                val = val.file_name
            elif isinstance( val, list ):
                val = ', '.join( val )
            rval['metadata_' + name] = val
        return rval

class LibraryDatasetDatasetAssociation( DatasetInstance ):
    def __init__( self,
                  copied_from_history_dataset_association=None,
                  copied_from_library_dataset_dataset_association=None,
                  library_dataset=None,
                  user=None,
                  sa_session=None,
                  **kwd ):
        # FIXME: sa_session is must be passed to DataSetInstance if the create_dataset 
        # parameter in kwd is True so that the new object can be flushed.  Is there a better way?
        DatasetInstance.__init__( self, sa_session=sa_session, **kwd )
        if copied_from_history_dataset_association:
            self.copied_from_history_dataset_association_id = copied_from_history_dataset_association.id
        if copied_from_library_dataset_dataset_association:
            self.copied_from_library_dataset_dataset_association_id = copied_from_library_dataset_dataset_association.id
        self.library_dataset = library_dataset
        self.user = user
    def to_history_dataset_association( self, target_history, parent_id = None, add_to_history = False ):
        hda = HistoryDatasetAssociation( name=self.name, 
                                         info=self.info,
                                         blurb=self.blurb, 
                                         peek=self.peek, 
                                         extension=self.extension, 
                                         dbkey=self.dbkey, 
                                         dataset=self.dataset, 
                                         visible=self.visible, 
                                         deleted=self.deleted, 
                                         parent_id=parent_id, 
                                         copied_from_library_dataset_dataset_association=self,
                                         history=target_history )
        object_session( self ).add( hda )
        object_session( self ).flush()
        hda.metadata = self.metadata #need to set after flushed, as MetadataFiles require dataset.id
        if add_to_history and target_history:
            target_history.add_dataset( hda )
        for child in self.children:
            child_copy = child.to_history_dataset_association( target_history = target_history, parent_id = hda.id, add_to_history = False )
        if not self.datatype.copy_safe_peek:
            hda.set_peek() #in some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
        object_session( self ).flush()
        return hda
    def copy( self, copy_children = False, parent_id = None, target_folder = None ):
        ldda = LibraryDatasetDatasetAssociation( name=self.name, 
                                                 info=self.info, 
                                                 blurb=self.blurb, 
                                                 peek=self.peek, 
                                                 extension=self.extension, 
                                                 dbkey=self.dbkey, 
                                                 dataset=self.dataset, 
                                                 visible=self.visible, 
                                                 deleted=self.deleted, 
                                                 parent_id=parent_id, 
                                                 copied_from_library_dataset_dataset_association=self,
                                                 folder=target_folder )
        object_session( self ).add( ldda )
        object_session( self ).flush()
         # Need to set after flushed, as MetadataFiles require dataset.id
        ldda.metadata = self.metadata
        if copy_children:
            for child in self.children:
                child_copy = child.copy( copy_children = copy_children, parent_id = ldda.id )
        if not self.datatype.copy_safe_peek:
             # In some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
            ldda.set_peek()
        object_session( self ).flush()
        return ldda
    def clear_associated_files( self, metadata_safe = False, purge = False ):
        return
    def get_access_roles( self, trans ):
        return self.dataset.get_access_roles( trans )
    def get_info_association( self, restrict=False, inherited=False ):
        # If restrict is True, we will return this ldda's info_association whether it
        # exists or not ( in which case None will be returned ).  If restrict is False,
        # we'll return the next available info_association in the inheritable hierarchy.
        # True is also returned if the info_association was inherited, and False if not.
        # This enables us to eliminate displaying any contents of the inherited template.
        if self.info_association:
            return self.info_association[0], inherited
        if restrict:
            return None, inherited
        return self.library_dataset.folder.get_info_association( inherited=True )
    def get_template_widgets( self, trans, get_contents=True ):
        # See if we have any associated templatesThe get_contents
        # param is passed by callers that are inheriting a template - these
        # are usually new library datsets for which we want to include template
        # fields on the upload form.
        info_association, inherited = self.get_info_association()
        if info_association:
            if inherited:
                template = info_association.template.current.latest_form
            else:
                template = info_association.template
            # See if we have any field contents, but only if the info_association was
            # not inherited ( we do not want to display the inherited contents ).
            if not inherited and get_contents:
                info = info_association.info
                if info:
                    return template.get_widgets( trans.user, info.content )
            else:
                return template.get_widgets( trans.user )
        return []
    def get_display_name( self ):
        """
        LibraryDatasetDatasetAssociation name can be either a string or a unicode object.
        If string, convert to unicode object assuming 'utf-8' format.
        """
        ldda_name = self.name
        if isinstance( ldda_name, str ):
            ldda_name = unicode( ldda_name, 'utf-8' )
        return ldda_name

class LibraryInfoAssociation( object ):
    def __init__( self, library, form_definition, info, inheritable=False ):
        self.library = library
        self.template = form_definition
        self.info = info
        self.inheritable = inheritable

class LibraryFolderInfoAssociation( object ):
    def __init__( self, folder, form_definition, info, inheritable=False ):
        self.folder = folder
        self.template = form_definition
        self.info = info
        self.inheritable = inheritable

class LibraryDatasetDatasetInfoAssociation( object ):
    def __init__( self, library_dataset_dataset_association, form_definition, info ):
        # TODO: need to figure out if this should be inheritable to the associated LibraryDataset
        self.library_dataset_dataset_association = library_dataset_dataset_association
        self.template = form_definition
        self.info = info

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

class CloudImage( object ):
    def __init__( self ):
        self.id = None
        self.instance_id = None
        self.state = None
        
class UCI( object ):
    def __init__( self ):
        self.id = None
        self.user = None

class CloudInstance( object ):
    def __init__( self ):
        self.id = None
        self.user = None
        self.name = None
        self.instance_id = None
        self.mi = None
        self.state = None
        self.public_dns = None
        self.availability_zone = None
        
class CloudStore( object ):
    def __init__( self ):
        self.id = None
        self.volume_id = None
        self.user = None
        self.size = None
        self.availability_zone = None
        
class CloudSnapshot( object ):
    def __init__( self ):
        self.id = None
        self.user = None
        self.store_id = None
        self.snapshot_id = None
        
class CloudProvider( object ):
    def __init__( self ):
        self.id = None
        self.user = None
        self.type = None

class CloudUserCredentials( object ):
    def __init__( self ):
        self.id = None
        self.user = None
        self.name = None
        self.accessKey = None
        self.secretKey = None
        self.credentials = []
 
class StoredWorkflow( object ):
    def __init__( self ):
        self.id = None
        self.user = None
        self.name = None
        self.slug = None
        self.published = False
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
        self.input_connections = []
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

class WorkflowInvocation( object ):
    pass

class WorkflowInvocationStep( object ):
    pass

class MetadataFile( object ):
    def __init__( self, dataset = None, name = None ):
        if isinstance( dataset, HistoryDatasetAssociation ):
            self.history_dataset = dataset
        elif isinstance( dataset, LibraryDatasetDatasetAssociation ):
            self.library_dataset = dataset
        self.name = name
    @property
    def file_name( self ):
        assert self.id is not None, "ID must be set before filename used (commit the object)"
        path = os.path.join( Dataset.file_path, '_metadata_files', *directory_hash_id( self.id ) )
        # Create directory if it does not exist
        try:
            os.makedirs( path )
        except OSError, e:
            # File Exists is okay, otherwise reraise
            if e.errno != errno.EEXIST:
                raise
        # Return filename inside hashed directory
        return os.path.abspath( os.path.join( path, "metadata_%d.dat" % self.id ) )

class FormDefinition( object ):
    types = Bunch(  REQUEST = 'Sequencing Request Form',
                    SAMPLE = 'Sequencing Sample Form',
                    LIBRARY_INFO_TEMPLATE = 'Library information template',
                    USER_INFO = 'User Information'  )
    def __init__(self, name=None, desc=None, fields=[], 
                 form_definition_current=None, form_type=None, layout=None):
        self.name = name
        self.desc = desc
        self.fields = fields 
        self.form_definition_current = form_definition_current
        self.type = form_type
        self.layout = layout
    def fields_of_grid(self, grid_index):
        '''
        This method returns the list of fields belonging to the given grid.
        '''
        gridfields = {}
        for i, f in enumerate(self.fields):
            if str(f['layout']) == str(grid_index):
                gridfields[i] = f
        return gridfields
    def get_widgets( self, user, contents=[], **kwd ):
        '''
        Return the list of widgets that comprise a form definition,
        including field contents if any.
        '''
        params = util.Params( kwd )
        widgets = []
        for index, field in enumerate( self.fields ):
            field_name = 'field_%i' % index
            # determine the value of the field
            if field_name in kwd:
                # the user had already filled out this field and the same form is re-rendered 
                # due to some reason like required fields have been left out.
                if field[ 'type' ] == 'CheckboxField':
                    value = CheckboxField.is_checked( params.get( field_name, False ) )
                else:
                    value = util.restore_text( params.get( field_name, '' ) )
            elif contents:
                try:
                    # This field has a saved value.
                    value = str( contents[ index ] )
                except:
                    # If there was an error getting the saved value, we'll still
                    # display the widget, but it will be empty.
                    if field[ 'type' ] == 'CheckboxField':
                        # Since we do not have contents, set checkbox value to False
                        value = False
                    else:
                        # Set other field types to empty string
                        value = '' 
            else:
                # if none of the above, then leave the field empty
                if field[ 'type' ] == 'CheckboxField':
                    # Since we do not have contents, set checkbox value to False
                    value = False
                else:
                    # Set other field types to the default value of the field
                    value = field.get('default', '')
            # create the field widget
            field_widget = eval( field[ 'type' ] )( field_name )
            if field[ 'type' ] == 'TextField':
                field_widget.set_size( 40 )
                field_widget.value = value
            elif field[ 'type' ] == 'TextArea':
                field_widget.set_size( 3, 40 )
                field_widget.value = value
            elif field['type'] == 'AddressField':
                field_widget.user = user
                field_widget.value = value
                field_widget.params = params
            elif field['type'] == 'WorkflowField':
                field_widget.user = user
                field_widget.value = value
                field_widget.params = params
            elif field[ 'type' ] == 'SelectField':
                for option in field[ 'selectlist' ]:
                    if option == value:
                        field_widget.add_option( option, option, selected=True )
                    else:
                        field_widget.add_option( option, option )
            elif field[ 'type' ] == 'CheckboxField':
                field_widget.set_checked( value )
            if field[ 'required' ] == 'required':
                req = 'Required'
            else:
                req = 'Optional'
            if field[ 'helptext' ]:
                helptext='%s (%s)' % ( field[ 'helptext' ], req )
            else:
                helptext = ''
            widgets.append( dict( label=field[ 'label' ],
                                  widget=field_widget,
                                  helptext=helptext ) )
        return widgets
        
class FormDefinitionCurrent( object ):
    def __init__(self, form_definition=None):
        self.latest_form = form_definition
        
class FormValues( object ):
    def __init__(self, form_def=None, content=None):
        self.form_definition = form_def
        self.content = content
        
class Request( object ):
    states = Bunch( NEW = 'New',
                    SUBMITTED = 'In Progress',
                    REJECTED = 'Rejected',
                    COMPLETE = 'Complete'   )
    def __init__(self, name=None, desc=None, request_type=None, user=None, 
                 form_values=None, notify=None):
        self.name = name
        self.desc = desc
        self.type = request_type
        self.values = form_values
        self.user = user
        self.notify = notify
        self.samples_list = []
    def state(self):
        if self.events:
            return self.events[0].state
        return None
    def last_comment(self):
        if self.events:
            if self.events[0].comment:
                return self.events[0].comment
            else:
                return ''
        return 'No comment'
    def has_sample(self, sample_name):
        for s in self.samples:
            if s.name == sample_name:
                return s
        return False
    def unsubmitted(self):
        return self.state() in [ self.states.REJECTED, self.states.NEW ]
    def rejected(self):
        return self.state() == self.states.REJECTED
    def submitted(self):
        return self.state() == self.states.SUBMITTED
    def new(self):
        return self.state() == self.states.NEW
    def complete(self):
        return self.state() == self.states.COMPLETE
    def sequence_run_ready(self):
        samples = []
        for s in self.samples:
            if not s.library:
                samples.append(s.name)
        return samples

    
class RequestEvent( object ):
    def __init__(self, request=None, request_state=None, comment=''):
        self.request = request
        self.state = request_state
        self.comment = comment
        
class RequestType( object ):
    rename_dataset_options = Bunch( NO = 'Do not rename',
                                    SAMPLE_NAME = 'Preprend sample name',
                                    EXPERIMENT_AND_SAMPLE_NAME = 'Prepend experiment and sample name')
    permitted_actions = get_permitted_actions( filter='REQUEST_TYPE' )
    def __init__(self, name=None, desc=None, request_form=None, sample_form=None,
                 datatx_info=None):
        self.name = name
        self.desc = desc
        self.request_form = request_form
        self.sample_form = sample_form
        self.datatx_info = datatx_info
        
class RequestTypePermissions( object ):
    def __init__( self, action, request_type, role ):
        self.action = action
        self.request_type = request_type
        self.role = role
    
class Sample( object ):
    transfer_status = Bunch( NOT_STARTED = 'Not started',
                             IN_QUEUE = 'In queue',
                             TRANSFERRING = 'Transferring dataset',
                             ADD_TO_LIBRARY = 'Adding to data library',
                             COMPLETE = 'Complete',
                             ERROR = 'Error')
    def __init__(self, name=None, desc=None, request=None, form_values=None, 
                 bar_code=None, library=None, folder=None, dataset_files=None):
        self.name = name
        self.desc = desc
        self.request = request
        self.values = form_values
        self.bar_code = bar_code
        self.library = library
        self.folder = folder
        self.dataset_files = dataset_files
    def current_state(self):
        if self.events:
            return self.events[0].state
        return None
    def untransferred_dataset_files(self):
        count = 0
        for df in self.dataset_files:
            if df['status'] == self.transfer_status.NOT_STARTED:
                count = count + 1
        return count
    def inprogress_dataset_files(self):
        count = 0
        for df in self.dataset_files:
            if df['status'] not in [self.transfer_status.NOT_STARTED, self.transfer_status.COMPLETE]:
                count = count + 1
        return count
    def transferred_dataset_files(self):
        count = 0
        for df in self.dataset_files:
            if df['status'] == self.transfer_status.COMPLETE:
                count = count + 1
        return count
    def dataset_size(self, filepath):
        def print_ticks(d):
            pass
        datatx_info = self.request.type.datatx_info
        cmd  = 'ssh %s@%s "du -sh \'%s\'"' % ( datatx_info['username'],
                                          datatx_info['host'],
                                          filepath)
        output = pexpect.run(cmd, events={'.ssword:*': datatx_info['password']+'\r\n', 
                                          pexpect.TIMEOUT:print_ticks}, 
                                          timeout=10)
        return output.split('\t')[0]

class SampleState( object ):
    def __init__(self, name=None, desc=None, request_type=None):
        self.name = name
        self.desc = desc
        self.request_type = request_type

class SampleEvent( object ):
    def __init__(self, sample=None, sample_state=None, comment=''):
        self.sample = sample
        self.state = sample_state
        self.comment = comment
        
class UserAddress( object ):
    def __init__(self, user=None, desc=None, name=None, institution=None, 
                 address=None, city=None, state=None, postal_code=None, 
                 country=None, phone=None):
        self.user = user
        self.desc = desc
        self.name = name
        self.institution = institution
        self.address = address
        self.city = city
        self.state = state
        self.postal_code = postal_code
        self.country = country
        self.phone = phone
    def get_html(self):
        html = ''
        if self.name:
            html = html + self.name
        if self.institution:
            html = html + '<br/>' + self.institution
        if self.address:
            html = html + '<br/>' + self.address
        if self.city:
            html = html + '<br/>' + self.city
        if self.state:
            html = html + ' ' + self.state
        if self.postal_code:
            html = html + ' ' + self.postal_code
        if self.country:
            html = html + '<br/>' + self.country
        if self.phone:
            html = html + '<br/>' + 'Phone: ' + self.phone
        return html

class Page( object ):
    def __init__( self ):
        self.id = None
        self.user = None
        self.title = None
        self.slug = None
        self.latest_revision_id = None
        self.revisions = []
        self.importable = None
        self.published = None

class PageRevision( object ):
    def __init__( self ):
        self.user = None
        self.title = None
        self.content = None
        
class PageUserShareAssociation( object ):
    def __init__( self ):
        self.page = None
        self.user = None

class Visualization( object ):
    def __init__( self ):
        self.id = None
        self.user = None
        self.type = None
        self.title = None
        self.latest_revision = None
        self.revisions = []

class VisualizationRevision( object ):
    def __init__( self ):
        self.id = None
        self.visualization = None
        self.title = None
        self.config = None
        
class VisualizationUserShareAssociation( object ):
    def __init__( self ):
        self.visualization = None
        self.user = None
        
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
        
class HistoryTagAssociation ( ItemTagAssociation ):
    pass
    
class DatasetTagAssociation ( ItemTagAssociation ):
    pass
    
class HistoryDatasetAssociationTagAssociation ( ItemTagAssociation ):
    pass

class PageTagAssociation ( ItemTagAssociation ):
    pass

class WorkflowStepTagAssociation ( ItemTagAssociation ):
    pass
    
class StoredWorkflowTagAssociation ( ItemTagAssociation ):
    pass
    
class VisualizationTagAssociation ( ItemTagAssociation ):
    pass
    
class HistoryAnnotationAssociation( object ):
    pass
    
class HistoryDatasetAssociationAnnotationAssociation( object ):
    pass
    
class StoredWorkflowAnnotationAssociation( object ):
    pass
    
class WorkflowStepAnnotationAssociation( object ):
    pass
    
class PageAnnotationAssociation( object ):
    pass
    
class VisualizationAnnotationAssociation( object ):
    pass
    
class UserPreference ( object ):
    def __init__( self, name=None, value=None ):
        self.name = name
        self.value = value
        
class UserAction( object ):
    def __init__( self, id=None, create_time=None, user_id=None, session_id=None, action=None, params=None, context=None):
        self.id = id
        self.create_time = create_time
        self.user_id = user_id
        self.session_id = session_id
        self.action = action
        self.params = params
        self.context = context

class APIKeys( object ):
    pass

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
