"""
Galaxy data model classes

Naming: try to use class names that have a distinct plural form so that
the relationship cardinalities are obvious (e.g. prefer Dataset to Data)
"""

import os.path, os, errno, copy
import sha
import galaxy.datatypes
from galaxy.util.bunch import Bunch
from galaxy import util
import tempfile
import galaxy.datatypes.registry
from galaxy.datatypes.metadata import MetadataCollection
from galaxy.security import RBACAgent

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
    def __init__( self, email=None, password=None ):
        self.email = email
        self.password = password
        self.external = False
        # Relationships
        self.histories = []
        
    def set_password_cleartext( self, cleartext ):
        """Set 'self.password' to the digest of 'cleartext'."""
        self.password = sha.new( cleartext ).hexdigest()
    def check_password( self, cleartext ):
        """Check if 'cleartext' matches 'self.password' when hashed."""
        return self.password == sha.new( cleartext ).hexdigest()
    
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

class GroupDatasetAssociation( object ):
    def __init__( self, group, dataset, permitted_actions=[] ):
        if isinstance( group,  GroupDatasetAssociation ) or \
           isinstance( group, DefaultUserGroupAssociation ) or \
           isinstance( group, DefaultHistoryGroupAssociation ):
            group = group.group
        self.group = group
        if isinstance( dataset, HistoryDatasetAssociation ):
            dataset = dataset.dataset
        self.dataset = dataset
        self.permitted_actions = permitted_actions
    def add_permitted_action( self, action ):
        if action not in self.permitted_actions:
            return self.permitted_actions.append( action )
        raise 'action (%s) already exists in permitted actions list (%s: %s).' % ( action, str( self.id ), str( self.permitted_actions ) )
    def remove_permitted_action( self, action ):
        return self.permitted_actions.remove( action )

class Group( object ):
    public_id = None
    permitted_actions = galaxy.security.get_permitted_actions( 'GROUP' )
    def __init__( self, name = None, priority = 0 ):
        self.name = name
        self.priority = priority
    @classmethod
    def get_public_group( cls ):
        return Group.get( cls.public_id )
    @classmethod
    def set_public_group( cls, group ):
        # We store the id instead of the object, because of alchemy sessions
        if isinstance( group, Group ):
            group = group.id
        cls.public_id = group
    @classmethod
    def guess_public_group( cls ):
        # Retrieve from database and store public group id
        group = Group.filter_by( name='public' ).first()
        cls.set_public_group( group )

class UserGroupAssociation( object ):
    def __init__( self, user, group ):
        self.user = user
        self.group = group

class DefaultUserGroupAssociation( object ):
    def __init__( self, user, group, permitted_actions ):
        if isinstance( group, GroupDatasetAssociation ) or \
           isinstance( group, DefaultUserGroupAssociation ) or \
           isinstance( group, DefaultHistoryGroupAssociation ):
            group = group.group
        self.user = user
        self.group = group
        self.permitted_actions = permitted_actions

class DefaultHistoryGroupAssociation( object ):
    def __init__( self, history, group, permitted_actions ):
        if isinstance( group, GroupDatasetAssociation ) or \
           isinstance( group, DefaultUserGroupAssociation ) or \
           isinstance( group, DefaultHistoryGroupAssociation ):
            group = group.group
        self.history = history
        self.group = group
        self.permitted_actions = permitted_actions

class History( object ):
    def __init__( self, id=None, name=None, user=None ):
        self.id = id
        self.name = name or "Unnamed history"
        self.deleted = False
        self.purged = False
        self.genome_build = None
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

    def copy(self):
        des = History()
        des.flush()
        des.name = self.name
        des.user_id = self.user_id
        for data in self.datasets:
            new_data = data.copy( copy_children = True )
            des.add_dataset( new_data )
            new_data.flush()
        des.hid_counter = self.hid_counter
        des.flush()
        return des

# class Query( object ):
#     def __init__( self, name=None, state=None, tool_parameters=None, history=None ):
#         self.name = name or "Unnamed query"
#         self.state = state
#         self.tool_parameters = tool_parameters
#         # Relationships
#         self.history = history
#         self.datasets = []

class Dataset( object ):
    states = Bunch( NEW = 'new',
                    QUEUED = 'queued',
                    RUNNING = 'running',
                    OK = 'ok',
                    EMPTY = 'empty',
                    ERROR = 'error',
                    DISCARDED = 'discarded' )
    permitted_actions = galaxy.security.get_permitted_actions( 'DATASET' )
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

    # FIXME: sqlalchemy will replace this
    def _delete(self):
        """Remove the file that corresponds to this data"""
        try:
            os.remove(self.data.file_name)
        except OSError, e:
            log.critical('%s delete error %s' % (self.__class__.__name__, e))

class DatasetInstance( object ):
    """A base class for all 'dataset instances', HDAs, LDAs, etc"""
    states = Dataset.states
    permitted_actions = Dataset.permitted_actions
    def __init__( self, id=None, hid=None, name=None, info=None, blurb=None, peek=None, extension=None, 
                  dbkey=None, metadata=None, history=None, dataset=None, deleted=False, designation=None,
                  parent_id=None, validation_errors=None, visible=True, create_dataset = False ):
        self.name = name or "Unnamed dataset"
        self.id = id
        self.info = info
        self.blurb = blurb
        self.peek = peek
        self.extension = extension
        self.dbkey = dbkey
        self.designation = designation
        self.metadata = metadata or dict()
        self.deleted = deleted
        self.visible = visible
        # Relationships
        if not dataset and create_dataset:
            dataset = Dataset()
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
        if not hasattr( self, '_metadata_collection' ):
            self._metadata_collection = MetadataCollection( self, self.datatype.metadata_spec )
        return self._metadata_collection
    def set_metadata( self, bunch ):
        # Needs to accept a MetadataCollection, a bunch, or a dict
        self._metadata = dict( [ ( key, copy.deepcopy( value ) ) for key, value in bunch.items() ] )
    metadata = property( get_metadata, set_metadata )
    # This provide backwards compatibility with using the old dbkey
    # field in the database.  That field now maps to "old_dbkey" (see mapping.py).
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
        if hasattr( self, '_metadata_collection' ):
            del self._metadata_collection
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
        raise 'Unimplemented'
    def get_child_by_designation(self, designation):
        for child in self.children:
            if child.designation == designation:
                return child
        return None
    def get_converter_types(self):
        return self.datatype.get_converter_types( self, datatypes_registry)
    def find_conversion_destination( self, accepted_formats, **kwd ):
        """Returns ( target_ext, exisiting converted dataset )"""
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

class HistoryDatasetAssociation( DatasetInstance ):
    def __init__( self, 
                  hid = None, 
                  history = None, 
                  copied_from_history_dataset_association = None, 
                  copied_from_library_folder_dataset_association = None, 
                  **kwd ):
        DatasetInstance.__init__( self, **kwd )
        self.hid = hid
        # Relationships
        self.history = history
        self.copied_from_history_dataset_association = copied_from_history_dataset_association
        self.copied_from_library_folder_dataset_association = copied_from_library_folder_dataset_association
    def copy( self, copy_children = False, parent_id = None, target_history = None ):
        des = HistoryDatasetAssociation( hid=self.hid, 
                                         name=self.name, 
                                         info=self.info, 
                                         blurb=self.blurb, 
                                         peek=self.peek, 
                                         extension=self.extension, 
                                         dbkey=self.dbkey, 
                                         metadata=self._metadata, 
                                         dataset = self.dataset, 
                                         visible=self.visible, 
                                         deleted=self.deleted, 
                                         parent_id=parent_id, 
                                         copied_from_history_dataset_association=self,
                                         history = target_history )
        des.flush()
        if copy_children:
            for child in self.children:
                child_copy = child.copy( copy_children = copy_children, parent_id = des.id )
        if not self.datatype.copy_safe_peek:
            des.set_peek() #in some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
        des.flush()
        return des
    def clear_associated_files( self, metadata_safe = False, purge = False ):
        #metadata_safe = True means to only clear when assoc.metadata_safe == False
        for assoc in self.implicitly_converted_datasets:
            if not metadata_safe or not assoc.metadata_safe:
                assoc.clear( purge = purge )

class History( object ):
    def __init__( self, id=None, name=None, user=None ):
        self.id = id
        self.name = name or "Unnamed history"
        self.deleted = False
        self.purged = False
        self.genome_build = None
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
            new_data = data.copy( copy_children = True, target_history = des )
            des.add_dataset( new_data, set_hid = False )
            new_data.flush()
        des.hid_counter = self.hid_counter
        des.flush()
        return des

class Library( object ):
    def __init__( self, name = None, description = None, root_folder = None ):
        self.name = name or "Unnamed library"
        self.description = description
        self.root_folder = root_folder

class LibraryFolder( object ):
    def __init__( self, name = None, description = None, item_count = 0, order_id = None ):
        self.name = name or "Unnamed folder"
        self.description = description
        self.item_count = item_count
        self.order_id = order_id
        self.genome_build = None
    def add_dataset( self, dataset, genome_build=None ):
        dataset.folder_id = self.id
        dataset.order_id = self.item_count
        self.item_count += 1
        if genome_build not in [None, '?']:
            self.genome_build = genome_build
    def add_folder( self, folder ):
        folder.parent_id = self.id
        folder.order_id = self.item_count
        self.item_count += 1

    @property
    def active_components( self ):
        return list( self.active_folders ) + list( self.active_datasets )

class LibraryFolderDatasetAssociation( DatasetInstance ):
    def __init__( self, 
                  folder = None, 
                  order_id = None, 
                  copied_from_history_dataset_association = None, 
                  copied_from_library_folder_dataset_association = None, 
                  **kwd ):
        DatasetInstance.__init__( self, **kwd )
        self.folder = folder
        self.order_id = order_id
        self.copied_from_history_dataset_association = copied_from_history_dataset_association
        self.copied_from_library_folder_dataset_association = copied_from_library_folder_dataset_association
    def to_history_dataset_association( self, parent_id = None, target_history = None ):
        if target_history:
            hid = target_history._next_hid()
        else:
            hid = None
        des = HistoryDatasetAssociation( name=self.name, 
                                         info=self.info, 
                                         blurb=self.blurb, 
                                         peek=self.peek, 
                                         extension=self.extension, 
                                         dbkey=self.dbkey, 
                                         metadata=self._metadata, 
                                         dataset = self.dataset, 
                                         visible=self.visible, 
                                         deleted=self.deleted, 
                                         parent_id=parent_id, 
                                         copied_from_library_folder_dataset_association = self,
                                         history = target_history,
                                         hid = hid )
        des.flush()
        for child in self.children:
            child_copy = child.to_history_dataset_association( parent_id = des.id )
        if not self.datatype.copy_safe_peek:
            des.set_peek() #in some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
        des.flush()
        return des
    def copy( self, copy_children = False, parent_id = None, target_folder = None ):
        des = LibraryFolderDatasetAssociation( name=self.name, 
                                               info=self.info, 
                                               blurb=self.blurb, 
                                               peek=self.peek, 
                                               extension=self.extension, 
                                               dbkey=self.dbkey, 
                                               metadata=self._metadata, 
                                               dataset = self.dataset, 
                                               visible=self.visible, 
                                               deleted=self.deleted, 
                                               parent_id=parent_id, 
                                               copied_from_library_folder_dataset_association = self,
                                               folder = target_folder )
        des.flush()
        if copy_children:
            for child in self.children:
                child_copy = child.copy( copy_children = copy_children, parent_id = des.id )
        if not self.datatype.copy_safe_peek:
            des.set_peek() #in some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
        des.flush()
        return des
    def clear_associated_files( self, metadata_safe = False, purge = False ):
        return

class LibraryTag( object ):
    def __init__( self, tag ):
        self.tag = tag

class LibraryTagFolderAssociation( object ):
    def __init__( self, tag, folder ):
        self.tag = tag
        self.folder = folder

class LibraryTagDatasetAssociation( object ):
    def __init__( self, tag, dataset ):
        self.tag = tag
        self.dataset = dataset

# class Query( object ):
#     def __init__( self, name=None, state=None, tool_parameters=None, history=None ):
#         self.name = name or "Unnamed query"
#         self.state = state
#         self.tool_parameters = tool_parameters
#         # Relationships
#         self.history = history
#         self.datasets = []

            
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
                  current_history_id=None, 
                  session_key=None, 
                  is_valid=False, 
                  prev_session_id=None ):
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
