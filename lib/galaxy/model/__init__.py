"""
Galaxy data model classes

Naming: try to use class names that have a distinct plural form so that
the relationship cardinalities are obvious (e.g. prefer Dataset to Data)
"""

import os.path, os, errno, sys
import galaxy.datatypes
from galaxy.util.bunch import Bunch
from galaxy import util
import tempfile
import galaxy.datatypes.registry
from galaxy.datatypes.metadata import MetadataCollection
from galaxy.security import RBACAgent, get_permitted_actions
from galaxy.util.hash_util import *
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
        self.deleted = False
        self.purged = False
        self.username = None
        # Relationships
        self.histories = []
        
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
            dataset.flush()
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
        new_history.flush()
        if activatable:
            hdas = self.activatable_datasets
        else:
            hdas = self.active_datasets
        for hda in hdas:
            new_hda = hda.copy( copy_children=True, target_history=new_history )
            new_history.add_dataset( new_hda, set_hid = False )
            new_hda.flush()
        new_history.hid_counter = self.hid_counter
        new_history.flush()
        return new_history
    @property
    def activatable_datasets( self ):
        # This needs to be a list
        return [ hda for hda in self.datasets if not hda.dataset.deleted ]

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
            if not self.file_size:
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
        self.designation = designation
        self.metadata = metadata or dict()
        if dbkey: #dbkey is stored in metadata, only set if non-zero, or else we could clobber one supplied by input 'metadata'
            self.dbkey = dbkey
        self.deleted = deleted
        self.visible = visible
        # Relationships
        if not dataset and create_dataset:
            dataset = Dataset( state=Dataset.states.NEW )
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
    def set_multi_byte_peek( self ):
        return self.datatype.set_multi_byte_peek( self )
    def init_meta( self, copy_from=None ):
        return self.datatype.init_meta( self, copy_from=copy_from )
    def set_meta( self, **kwd ):
        self.clear_associated_files( metadata_safe = True )
        return self.datatype.set_meta( self, **kwd )
    def set_readonly_meta( self, **kwd ):
        return self.datatype.set_readonly_meta( self, **kwd )
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

class HistoryDatasetAssociation( DatasetInstance ):
    def __init__( self, 
                  hid = None, 
                  history = None, 
                  copied_from_history_dataset_association = None, 
                  copied_from_library_dataset_dataset_association = None, 
                  **kwd ):
        DatasetInstance.__init__( self, **kwd )
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
        hda.flush()
        hda.set_size()
        # Need to set after flushed, as MetadataFiles require dataset.id
        hda.metadata = self.metadata
        if copy_children:
            for child in self.children:
                child_copy = child.copy( copy_children = copy_children, parent_id = hda.id )
        if not self.datatype.copy_safe_peek:
            # In some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
            hda.set_peek()
        hda.flush()
        return hda
    def to_library_dataset_dataset_association( self, target_folder, replace_dataset=None, parent_id=None, user=None ):
        if replace_dataset:
            # The replace_dataset param ( when not None ) refers to a LibraryDataset that is being replaced with a new version.
            library_dataset = replace_dataset
        else:
            # If replace_dataset is None, the Library level permissions will be taken from the folder and applied to the new 
            # LibraryDataset, and the current user's DefaultUserPermissions will be applied to the associated Dataset.
            library_dataset = LibraryDataset( folder=target_folder, name=self.name, info=self.info )
            library_dataset.flush()
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
        ldda.flush()
        # Permissions must be the same on the LibraryDatasetDatasetAssociation and the associated LibraryDataset
        # Must set metadata after ldda flushed, as MetadataFiles require ldda.id
        ldda.metadata = self.metadata
        if not replace_dataset:
            target_folder.add_library_dataset( library_dataset, genome_build=ldda.dbkey )
            target_folder.flush()
        library_dataset.library_dataset_dataset_association_id = ldda.id
        library_dataset.flush()
        for child in self.children:
            child_copy = child.to_library_dataset_dataset_association( target_folder=target_folder,
                                                                       replace_dataset=replace_dataset,
                                                                       parent_id=ldda.id,
                                                                       user=ldda.user )
        if not self.datatype.copy_safe_peek:
            # In some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
            ldda.set_peek()
        ldda.flush()
        return ldda
    def clear_associated_files( self, metadata_safe = False, purge = False ):
        # metadata_safe = True means to only clear when assoc.metadata_safe == False
        for assoc in self.implicitly_converted_datasets:
            if not metadata_safe or not assoc.metadata_safe:
                assoc.clear( purge = purge )

class HistoryDatasetAssociationDisplayAtAuthorization( object ):
    def __init__( self, hda=None, user=None, site=None ):
        self.history_dataset_association = hda
        self.user = user
        self.site = site

class Library( object ):
    permitted_actions = get_permitted_actions( filter='LIBRARY' )
    def __init__( self, name = None, description = None, root_folder = None ):
        self.name = name or "Unnamed library"
        self.description = description
        self.root_folder = root_folder
    def get_info_association( self, restrict=False ):
        if self.info_association:
            return self.info_association[0]
        return None

class LibraryFolder( object ):
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
    def get_info_association( self, restrict=False ):
        # If restrict is True, we will return this folder's info_association, not inheriting.
        # If restrict is False, we'll return the next available info_association in the
        # inheritable hierarchy
        if self.info_association:
            return self.info_association[0]
        if restrict:
            return None
        if self.parent:
            return self.parent.get_info_association()
        if self.library_root:
            return self.library_root[0].get_info_association()
        return None
    @property
    def active_library_datasets( self ):
         # This needs to be a list
        return [ ld for ld in self.datasets if not ld.library_dataset_dataset_association.deleted ]
    @property
    def activatable_library_datasets( self ):
         # This needs to be a list
        return [ ld for ld in self.datasets if not ld.library_dataset_dataset_association.dataset.deleted ]
    @property
    def active_datasets( self ):
         # This needs to be a list
        return [ ld.library_dataset_dataset_association.dataset for ld in self.datasets if not ld.library_dataset_dataset_association.deleted ]

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
        ldda.flush()
        self.flush()
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

class LibraryDatasetDatasetAssociation( DatasetInstance ):
    def __init__( self,
                  copied_from_history_dataset_association=None,
                  copied_from_library_dataset_dataset_association=None,
                  library_dataset=None,
                  user=None,
                  **kwd ):
        DatasetInstance.__init__( self, **kwd )
        self.copied_from_history_dataset_association = copied_from_history_dataset_association
        self.copied_from_library_dataset_dataset_association = copied_from_library_dataset_dataset_association
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
        hda.flush()
        hda.metadata = self.metadata #need to set after flushed, as MetadataFiles require dataset.id
        if add_to_history and target_history:
            target_history.add_dataset( hda )
        for child in self.children:
            child_copy = child.to_history_dataset_association( target_history = target_history, parent_id = hda.id, add_to_history = False )
        if not self.datatype.copy_safe_peek:
            hda.set_peek() #in some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
        hda.flush()
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
        ldda.flush()
         # Need to set after flushed, as MetadataFiles require dataset.id
        ldda.metadata = self.metadata
        if copy_children:
            for child in self.children:
                child_copy = child.copy( copy_children = copy_children, parent_id = ldda.id )
        if not self.datatype.copy_safe_peek:
             # In some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
            ldda.set_peek()
        ldda.flush()
        return ldda
    def clear_associated_files( self, metadata_safe = False, purge = False ):
        return
    def get_info_association( self, restrict=False ):
        # If restrict is True, we will return this ldda's info_association whether it
        # exists or not.  If restrict is False, we'll return the next available info_association
        # in the inheritable hierarchy
        if self.info_association:
            return self.info_association[0]
        if restrict:
            return None
        return self.library_dataset.folder.get_info_association()

class LibraryInfoAssociation( object ):
    def __init__( self, library, form_definition, info ):
        self.library = library
        self.template = form_definition
        self.info = info

class LibraryFolderInfoAssociation( object ):
    def __init__( self, folder, form_definition, info ):
        self.folder = folder
        self.template = form_definition
        self.info = info

class LibraryDatasetDatasetInfoAssociation( object ):
    def __init__( self, library_dataset_dataset_association, form_definition, info ):
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
                    LIBRARY_INFO_TEMPLATE = 'Library information template'  )
    def __init__(self, name=None, desc=None, fields=[], current_form=None, form_type=None, layout=None):
        self.name = name
        self.desc = desc
        self.fields = fields 
        self.form_definition_current = current_form
        self.type = form_type
        self.layout = layout
    def fields_of_grid(self, layout_grid_name):
        fields_dict = {}
        if not layout_grid_name:
            for i, f in enumerate(self.fields):
                fields_dict[i] = f
        else:
            layout_index = -1
            for index, lg_name in enumerate(self.layout):
                if lg_name == layout_grid_name:
                    layout_index = index
                    break
            for i, f in enumerate(self.fields):
                if f['layout'] == str(layout_index):
                    fields_dict[i] = f
        return fields_dict
        
class FormDefinitionCurrent( object ):
    def __init__(self, form_definition=None):
        self.latest_form = form_definition
        
class FormValues( object ):
    def __init__(self, form_def=None, content=None):
        self.form_definition = form_def
        self.content = content
        
class Request( object ):
    states = Bunch( UNSUBMITTED = 'Unsubmitted',
                    SUBMITTED = 'Submitted',
                    COMPLETE = 'Complete')
    def __init__(self, name=None, desc=None, request_type=None, user=None, 
                 form_values=None, library=None, folder=None, state=False):
        self.name = name
        self.desc = desc
        self.type = request_type
        self.values = form_values
        self.user = user
        self.library = library
        self.folder = folder
        self.state = state
        self.samples_list = []
    def add_sample(self, sample_name=None, sample_desc=None, sample_values=None):
        # create a form_values row
        values = trans.app.model.FormValues(self.type.sample_form, sample_values)
        values.flush()   
        sample = Sample(sample_name, sample_desc, self, values)
        sample.flush()
        # set the initial state            
        state = self.type.states[0]
        event = SampleEvent(sample, state)
        event.flush()
        # add this sample to the member array
        self.samples_list.append(sample)
        return sample
    def delete_sample(self, sample_name):
        pass
    def has_sample(self, sample_name):
        for s in self.samples:
            if s.name == sample_name:
                return s
        return False
    def submitted(self):
        return self.state == self.states.SUBMITTED
    def unsubmitted(self):
        return self.state == self.states.UNSUBMITTED
    def complete(self):
        return self.state == self.states.COMPLETE
        
class RequestType( object ):
    def __init__(self, name=None, desc=None, request_form=None, sample_form=None):
        self.name = name
        self.desc = desc
        self.request_form = request_form
        self.sample_form = sample_form
    
class Sample( object ):
    def __init__(self, name=None, desc=None, request=None, form_values=None, bar_code=None):
        self.name = name
        self.desc = desc
        self.request = request
        self.values = form_values
        self.bar_code = bar_code
    def current_state(self):
        return self.events[0].state

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
    def display(self):
        return  self.name+'<br/>'+ \
                self.institution+'<br/>'+ \
                self.address+'<br/>'+ \
                self.city+' '+self.state+' '+self.postal_code+'<br/>'+ \
                self.country+'<br/>'+ \
                'Phone: '+self.phone
    def get_html(self):
        return  self.name+'<br/>'+ \
                self.institution+'<br/>'+ \
                self.address+'<br/>'+ \
                self.city+' '+self.state+' '+self.postal_code+'<br/>'+ \
                self.country+'<br/>'+ \
                'Phone: '+self.phone
                
class Page( object ):
    def __init__( self ):
        self.id = None
        self.user = None
        self.title = None
        self.slug = None
        self.latest_revision_id = None
        self.revisions = []

class PageRevision( object ):
    def __init__( self ):
        self.user = None
        self.title = None
        self.content = None
        
class Tag ( object ):
    def __init__( self, id=None, type=None, parent_id=None, name=None ):
        self.id = id
        self.type = type
        self.parent_id = parent_id
        self.name = name
        
    def __str__ ( self ):
        return "Tag(id=%s, type=%i, parent_id=%s, name=%s)" %  ( self.id, self.type, self.parent_id, self.name )
    
class ItemTagAssociation ( object ):
    def __init__( self, id=None, item_id=None, tag_id=None, user_tname=None, value=None ):
        self.id = id
        self.item_id = item_id
        self.tag_id = tag_id
        self.user_tname = user_tname
        self.value = None
        self.user_value = None
        
    def __str__ ( self ):
        return "%s(item_id=%s, item_tag=%s, user_tname=%s, value=%s, user_value=%s)" % (self.__class__.__name__, self.item_id, self.tag_id, self.user_tname, self.value. self.user_value )  
    
    
class HistoryTagAssociation ( ItemTagAssociation ):
    pass

class DatasetTagAssociation ( ItemTagAssociation ):
    pass
    
class HistoryDatasetAssociationTagAssociation ( ItemTagAssociation ):
    pass

class PageTagAssociation ( ItemTagAssociation ):
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


