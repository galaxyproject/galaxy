import sys, logging, os, time, datetime, errno

log = logging.getLogger( __name__ )
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler( sys.stdout )
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter( format )
handler.setFormatter( formatter )
log.addHandler( handler )

from migrate import migrate_engine
from sqlalchemy import and_

from sqlalchemy import *
now = datetime.datetime.utcnow
from sqlalchemy.orm import *

from galaxy.model.orm.ext.assignmapper import assign_mapper

from galaxy.model.custom_types import *

from galaxy.util.bunch import Bunch


metadata = MetaData( migrate_engine )
context = scoped_session( sessionmaker( autoflush=False, autocommit=True ) )


## classes
def get_permitted_actions( **kwds ):
    return Bunch()

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


class Dataset( object ):
    states = Bunch( NEW = 'new',
                    UPLOAD = 'upload',
                    QUEUED = 'queued',
                    RUNNING = 'running',
                    OK = 'ok',
                    EMPTY = 'empty',
                    ERROR = 'error',
                    DISCARDED = 'discarded' )
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
            context.add( dataset )
            context.flush()
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
        context.add( self.dataset )
        context.flush() #flush here, because hda.flush() won't flush the Dataset object
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
        if not hasattr( self, '_metadata_collection' ) or self._metadata_collection.parent != self: #using weakref to store parent (to prevent circ ref), does a context.clear() cause parent to be invalidated, while still copying over this non-database attribute?
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
        context.add( hda )
        context.flush()
        hda.set_size()
        # Need to set after flushed, as MetadataFiles require dataset.id
        hda.metadata = self.metadata
        if copy_children:
            for child in self.children:
                child_copy = child.copy( copy_children = copy_children, parent_id = hda.id )
        if not self.datatype.copy_safe_peek:
            # In some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
            hda.set_peek()
        context.flush()
        return hda
    def to_library_dataset_dataset_association( self, target_folder, replace_dataset=None, parent_id=None ):
        if replace_dataset:
            # The replace_dataset param ( when not None ) refers to a LibraryDataset that is being replaced with a new version.
            library_dataset = replace_dataset
        else:
            # If replace_dataset is None, the Library level permissions will be taken from the folder and applied to the new 
            # LibraryDataset, and the current user's DefaultUserPermissions will be applied to the associated Dataset.
            library_dataset = LibraryDataset( folder=target_folder, name=self.name, info=self.info )
            context.add( library_dataset )
            context.flush()
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
                                                 user=self.history.user )
        context.add( ldda )
        context.flush()
        # Permissions must be the same on the LibraryDatasetDatasetAssociation and the associated LibraryDataset
        # Must set metadata after ldda flushed, as MetadataFiles require ldda.id
        ldda.metadata = self.metadata
        if not replace_dataset:
            target_folder.add_library_dataset( library_dataset, genome_build=ldda.dbkey )
            context.add( target_folder )
            context.flush()
        library_dataset.library_dataset_dataset_association_id = ldda.id
        context.add( library_dataset )
        context.flush()
        for child in self.children:
            child_copy = child.to_library_dataset_dataset_association( target_folder=target_folder, replace_dataset=replace_dataset, parent_id=ldda.id )
        if not self.datatype.copy_safe_peek:
            # In some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
            ldda.set_peek()
        context.flush()
        return ldda
    def clear_associated_files( self, metadata_safe = False, purge = False ):
        # metadata_safe = True means to only clear when assoc.metadata_safe == False
        for assoc in self.implicitly_converted_datasets:
            if not metadata_safe or not assoc.metadata_safe:
                assoc.clear( purge = purge )



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
    def to_history_dataset_association( self, target_history, parent_id=None ):
        hid = target_history._next_hid()
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
                                         history=target_history,
                                         hid=hid )
        context.flush()
        hda.metadata = self.metadata #need to set after flushed, as MetadataFiles require dataset.id
        for child in self.children:
            child_copy = child.to_history_dataset_association( target_history=target_history, parent_id=hda.id )
        if not self.datatype.copy_safe_peek:
            hda.set_peek() #in some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
        context.add( hda )
        context.flush()
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
        context.add( ldda )
        context.flush()
         # Need to set after flushed, as MetadataFiles require dataset.id
        ldda.metadata = self.metadata
        if copy_children:
            for child in self.children:
                child_copy = child.copy( copy_children = copy_children, parent_id = ldda.id )
        if not self.datatype.copy_safe_peek:
             # In some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
            ldda.set_peek()
        context.flush()
        return ldda
    def clear_associated_files( self, metadata_safe = False, purge = False ):
        return
    def get_library_item_info_templates( self, template_list=[], restrict=False ):
        # If restrict is True, we'll return only those templates directly associated with this LibraryDatasetDatasetAssociation
        if self.library_dataset_dataset_info_template_associations:
            template_list.extend( [ lddita.library_item_info_template for lddita in self.library_dataset_dataset_info_template_associations if lddita.library_item_info_template not in template_list ] )
        self.library_dataset.get_library_item_info_templates( template_list, restrict )
        return template_list



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
        context.add_all( ( self, ldda ) )
        context.flush()
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
    def get_library_item_info_templates( self, template_list=[], restrict=False ):
        # If restrict is True, we'll return only those templates directly associated with this LibraryDataset
        if self.library_dataset_info_template_associations:
            template_list.extend( [ ldita.library_item_info_template for ldita in self.library_dataset_info_template_associations if ldita.library_item_info_template not in template_list ] )
        if restrict not in [ 'True', True ]:
            self.folder.get_library_item_info_templates( template_list, restrict )
        return template_list

##tables


Dataset.table = Table( "dataset", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, index=True, default=now, onupdate=now ),
    Column( "state", TrimmedString( 64 ) ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "purged", Boolean, index=True, default=False ),
    Column( "purgable", Boolean, default=True ),
    Column( "external_filename" , TEXT ),
    Column( "_extra_files_path", TEXT ),
    Column( 'file_size', Numeric( 15, 0 ) ) )



HistoryDatasetAssociation.table = Table( "history_dataset_association", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "copied_from_history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id" ), nullable=True ),
    Column( "copied_from_library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), nullable=True ),
    Column( "hid", Integer ),
    Column( "name", TrimmedString( 255 ) ),
    Column( "info", TrimmedString( 255 ) ),
    Column( "blurb", TrimmedString( 255 ) ),
    Column( "peek" , TEXT ),
    Column( "extension", TrimmedString( 64 ) ),
    Column( "metadata", MetadataType(), key="_metadata" ),
    Column( "parent_id", Integer, ForeignKey( "history_dataset_association.id" ), nullable=True ),
    Column( "designation", TrimmedString( 255 ) ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "visible", Boolean ) )


LibraryDatasetDatasetAssociation.table = Table( "library_dataset_dataset_association", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "library_dataset_id", Integer, ForeignKey( "library_dataset.id" ), index=True ),
    Column( "dataset_id", Integer, ForeignKey( "dataset.id" ), index=True ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "copied_from_history_dataset_association_id", Integer, ForeignKey( "history_dataset_association.id", use_alter=True, name='history_dataset_association_dataset_id_fkey' ), nullable=True ),
    Column( "copied_from_library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id", use_alter=True, name='library_dataset_dataset_association_id_fkey' ), nullable=True ),
    Column( "name", TrimmedString( 255 ) ),
    Column( "info", TrimmedString( 255 ) ),
    Column( "blurb", TrimmedString( 255 ) ),
    Column( "peek" , TEXT ),
    Column( "extension", TrimmedString( 64 ) ),
    Column( "metadata", MetadataType(), key="_metadata" ),
    Column( "parent_id", Integer, ForeignKey( "library_dataset_dataset_association.id" ), nullable=True ),
    Column( "designation", TrimmedString( 255 ) ),
    Column( "deleted", Boolean, index=True, default=False ),
    Column( "visible", Boolean ),
    Column( "message", TrimmedString( 255 ) ) )

LibraryDataset.table = Table( "library_dataset", metadata, 
    Column( "id", Integer, primary_key=True ),
    Column( "library_dataset_dataset_association_id", Integer, ForeignKey( "library_dataset_dataset_association.id", use_alter=True, name="library_dataset_dataset_association_id_fk" ), nullable=True, index=True ),#current version of dataset, if null, there is not a current version selected
    Column( "order_id", Integer ),
    Column( "create_time", DateTime, default=now ),
    Column( "update_time", DateTime, default=now, onupdate=now ),
    Column( "name", TrimmedString( 255 ), key="_name" ), #when not None/null this will supercede display in library (but not when imported into user's history?)
    Column( "info", TrimmedString( 255 ),  key="_info" ), #when not None/null this will supercede display in library (but not when imported into user's history?)
    Column( "deleted", Boolean, index=True, default=False ) )



##mappers


assign_mapper( context, Dataset, Dataset.table,
    properties=dict( 
        history_associations=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( Dataset.table.c.id == HistoryDatasetAssociation.table.c.dataset_id ) ),
        active_history_associations=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( ( Dataset.table.c.id == HistoryDatasetAssociation.table.c.dataset_id ) & ( HistoryDatasetAssociation.table.c.deleted == False ) ) ),
        library_associations=relation( 
            LibraryDatasetDatasetAssociation, 
            primaryjoin=( Dataset.table.c.id == LibraryDatasetDatasetAssociation.table.c.dataset_id ) ),
        active_library_associations=relation( 
            LibraryDatasetDatasetAssociation, 
            primaryjoin=( ( Dataset.table.c.id == LibraryDatasetDatasetAssociation.table.c.dataset_id ) & ( LibraryDatasetDatasetAssociation.table.c.deleted == False ) ) )
            ) )


assign_mapper( context, HistoryDatasetAssociation, HistoryDatasetAssociation.table,
    properties=dict( 
        dataset=relation( 
            Dataset, 
            primaryjoin=( Dataset.table.c.id == HistoryDatasetAssociation.table.c.dataset_id ), lazy=False ),
        # .history defined in History mapper
        copied_to_history_dataset_associations=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( HistoryDatasetAssociation.table.c.copied_from_history_dataset_association_id == HistoryDatasetAssociation.table.c.id ),
            backref=backref( "copied_from_history_dataset_association", primaryjoin=( HistoryDatasetAssociation.table.c.copied_from_history_dataset_association_id == HistoryDatasetAssociation.table.c.id ), remote_side=[HistoryDatasetAssociation.table.c.id], uselist=False ) ),
        copied_to_library_dataset_dataset_associations=relation( 
            LibraryDatasetDatasetAssociation, 
            primaryjoin=( HistoryDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ),
            backref=backref( "copied_from_history_dataset_association", primaryjoin=( HistoryDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ), remote_side=[LibraryDatasetDatasetAssociation.table.c.id], uselist=False ) ),
        children=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( HistoryDatasetAssociation.table.c.parent_id == HistoryDatasetAssociation.table.c.id ),
            backref=backref( "parent", primaryjoin=( HistoryDatasetAssociation.table.c.parent_id == HistoryDatasetAssociation.table.c.id ), remote_side=[HistoryDatasetAssociation.table.c.id], uselist=False ) ),
        visible_children=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( ( HistoryDatasetAssociation.table.c.parent_id == HistoryDatasetAssociation.table.c.id ) & ( HistoryDatasetAssociation.table.c.visible == True ) ) )
            ) )

assign_mapper( context, LibraryDatasetDatasetAssociation, LibraryDatasetDatasetAssociation.table,
    properties=dict( 
        dataset=relation( Dataset ),
        library_dataset = relation( LibraryDataset,
        primaryjoin=( LibraryDatasetDatasetAssociation.table.c.library_dataset_id == LibraryDataset.table.c.id ) ),
        copied_to_library_dataset_dataset_associations=relation( 
            LibraryDatasetDatasetAssociation, 
            primaryjoin=( LibraryDatasetDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ),
            backref=backref( "copied_from_library_dataset_dataset_association", primaryjoin=( LibraryDatasetDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ), remote_side=[LibraryDatasetDatasetAssociation.table.c.id] ) ),
        copied_to_history_dataset_associations=relation( 
            HistoryDatasetAssociation, 
            primaryjoin=( HistoryDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ),
            backref=backref( "copied_from_library_dataset_dataset_association", primaryjoin=( HistoryDatasetAssociation.table.c.copied_from_library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ), remote_side=[LibraryDatasetDatasetAssociation.table.c.id], uselist=False ) ),
        children=relation( 
            LibraryDatasetDatasetAssociation, 
            primaryjoin=( LibraryDatasetDatasetAssociation.table.c.parent_id == LibraryDatasetDatasetAssociation.table.c.id ),
            backref=backref( "parent", primaryjoin=( LibraryDatasetDatasetAssociation.table.c.parent_id == LibraryDatasetDatasetAssociation.table.c.id ), remote_side=[LibraryDatasetDatasetAssociation.table.c.id] ) ),
        visible_children=relation( 
            LibraryDatasetDatasetAssociation, 
            primaryjoin=( ( LibraryDatasetDatasetAssociation.table.c.parent_id == LibraryDatasetDatasetAssociation.table.c.id ) & ( LibraryDatasetDatasetAssociation.table.c.visible == True ) ) )
        ) )

assign_mapper( context, LibraryDataset, LibraryDataset.table,
    properties=dict( 
        library_dataset_dataset_association=relation( LibraryDatasetDatasetAssociation, primaryjoin=( LibraryDataset.table.c.library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ) ),
        expired_datasets = relation( LibraryDatasetDatasetAssociation, foreign_keys=[LibraryDataset.table.c.id,LibraryDataset.table.c.library_dataset_dataset_association_id ], primaryjoin=( ( LibraryDataset.table.c.id == LibraryDatasetDatasetAssociation.table.c.library_dataset_id ) & ( not_( LibraryDataset.table.c.library_dataset_dataset_association_id == LibraryDatasetDatasetAssociation.table.c.id ) ) ), viewonly=True, uselist=True )
        ) )


def __guess_dataset_by_filename( filename ):
    """Return a guessed dataset by filename"""
    try:
        fields = os.path.split( filename )
        if fields:
            if fields[-1].startswith( 'dataset_' ) and fields[-1].endswith( '.dat' ): #dataset_%d.dat
                return Dataset.get( int( fields[-1][ len( 'dataset_' ): -len( '.dat' ) ] ) )
    except:
        pass #some parsing error, we can't guess Dataset
    return None

def upgrade():
    log.debug( "Fixing a discrepancy concerning deleted shared history items." )
    affected_items = 0
    start_time = time.time()
    for dataset in context.query( Dataset ).filter( and_( Dataset.deleted == True, Dataset.purged == False ) ):
        for dataset_instance in dataset.history_associations + dataset.library_associations:
            if not dataset_instance.deleted:
                dataset.deleted = False
                if dataset.file_size in [ None, 0 ]:
                    dataset.set_size() #Restore filesize
                affected_items += 1
                break
    context.flush()
    log.debug( "%i items affected, and restored." % ( affected_items ) )
    log.debug( "Time elapsed: %s" % ( time.time() - start_time ) )
    
    #fix share before hda
    log.debug( "Fixing a discrepancy concerning cleaning up deleted history items shared before HDAs." )
    dataset_by_filename = {}
    changed_associations = 0
    start_time = time.time()
    for dataset in context.query( Dataset ).filter( Dataset.external_filename.like( '%dataset_%.dat' ) ):
        if dataset.file_name in dataset_by_filename:
            guessed_dataset = dataset_by_filename[ dataset.file_name ]
        else:
            guessed_dataset = __guess_dataset_by_filename( dataset.file_name )
            if guessed_dataset and dataset.file_name != guessed_dataset.file_name:#not os.path.samefile( dataset.file_name, guessed_dataset.file_name ):
                guessed_dataset = None
            dataset_by_filename[ dataset.file_name ] = guessed_dataset
        
        if guessed_dataset is not None and guessed_dataset.id != dataset.id: #could we have a self referential dataset?
            for dataset_instance in dataset.history_associations + dataset.library_associations:
                dataset_instance.dataset = guessed_dataset
                changed_associations += 1
            #mark original Dataset as deleted and purged, it is no longer in use, but do not delete file_name contents
            dataset.deleted = True
            dataset.external_filename = "Dataset was result of share before HDA, and has been replaced: %s mapped to Dataset %s" % ( dataset.external_filename, guessed_dataset.id )
            dataset.purged = True #we don't really purge the file here, but we mark it as purged, since this dataset is now defunct
    context.flush()
    log.debug( "%i items affected, and restored." % ( changed_associations ) )
    log.debug( "Time elapsed: %s" % ( time.time() - start_time ) )

def downgrade():
    log.debug( "Downgrade is not possible." )
    
