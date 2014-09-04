"""
Galaxy Metadata

"""

import copy
import cPickle
import json
import os
import shutil
import sys
import tempfile
import weakref

from os.path import abspath

from galaxy import eggs
eggs.require( "SQLAlchemy >= 0.4" )
from sqlalchemy.orm import object_session

import galaxy.model
from galaxy.util import listify
from galaxy.util import stringify_dictionary_keys
from galaxy.util import string_as_bool
from galaxy.util import in_directory
from galaxy.util.odict import odict
from galaxy.web import form_builder

import logging
log = logging.getLogger(__name__)

STATEMENTS = "__galaxy_statements__" #this is the name of the property in a Datatype class where new metadata spec element Statements are stored

class Statement( object ):
    """
    This class inserts its target into a list in the surrounding
    class.  the data.Data class has a metaclass which executes these
    statements.  This is how we shove the metadata element spec into
    the class.
    """
    def __init__( self, target ):
        self.target = target

    def __call__( self, *args, **kwargs ):
        class_locals = sys._getframe( 1 ).f_locals #get the locals dictionary of the frame object one down in the call stack (i.e. the Datatype class calling MetadataElement)
        statements = class_locals.setdefault( STATEMENTS, [] ) #get and set '__galaxy_statments__' to an empty list if not in locals dict
        statements.append( ( self, args, kwargs ) ) #add Statement containing info to populate a MetadataElementSpec

    @classmethod
    def process( cls, element ):
        for statement, args, kwargs in getattr( element, STATEMENTS, [] ):
            statement.target( element, *args, **kwargs ) #statement.target is MetadataElementSpec, element is a Datatype class


class MetadataCollection( object ):
    """
    MetadataCollection is not a collection at all, but rather a proxy
    to the real metadata which is stored as a Dictionary. This class
    handles processing the metadata elements when they are set and
    retrieved, returning default values in cases when metadata is not set.
    """
    def __init__(self, parent ):
        self.parent = parent
        #initialize dict if needed
        if self.parent._metadata is None:
            self.parent._metadata = {}

    def get_parent( self ):
        if "_parent" in self.__dict__:
            return self.__dict__["_parent"]()
        return None

    def set_parent( self, parent ):
        self.__dict__["_parent"] = weakref.ref( parent ) # use weakref to prevent a circular reference interfering with garbage collection: hda/lda (parent) <--> MetadataCollection (self) ; needs to be hashable, so cannot use proxy.
    parent = property( get_parent, set_parent )

    @property
    def spec( self ):
        return self.parent.datatype.metadata_spec

    def __iter__( self ):
        return self.parent._metadata.__iter__()

    def get( self, key, default=None ):
        try:
            return self.__getattr__( key ) or default
        except:
            return default

    def items(self):
        return iter( [ ( k, self.get( k ) ) for k in self.spec.iterkeys() ] )

    def __str__(self):
        return dict( self.items() ).__str__()

    def __nonzero__( self ):
        return bool( self.parent._metadata )

    def __getattr__( self, name ):
        if name in self.spec:
            if name in self.parent._metadata:
                return self.spec[name].wrap( self.parent._metadata[name], object_session( self.parent ) )
            return self.spec[name].wrap( self.spec[name].default, object_session( self.parent ) )
        if name in self.parent._metadata:
            return self.parent._metadata[name]

    def __setattr__( self, name, value ):
        if name == "parent":
            return self.set_parent( value )
        else:
            if name in self.spec:
                self.parent._metadata[name] = self.spec[name].unwrap( value )
            else:
                self.parent._metadata[name] = value

    def element_is_set( self, name ):
        return bool( self.parent._metadata.get( name, False ) )

    def get_html_by_name( self, name, **kwd ):
        if name in self.spec:
            rval = self.spec[name].param.get_html( value=getattr( self, name ), context=self, **kwd )
            if rval is None:
                return self.spec[name].no_value
            return rval

    def make_dict_copy( self, to_copy ):
        """Makes a deep copy of input iterable to_copy according to self.spec"""
        rval = {}
        for key, value in to_copy.items():
            if key in self.spec:
                rval[key] = self.spec[key].param.make_copy( value, target_context=self, source_context=to_copy )
        return rval

    def from_JSON_dict( self, filename=None, path_rewriter=None, json_dict=None ):
        dataset = self.parent
        if filename is not None:
            log.debug( 'loading metadata from file for: %s %s' % ( dataset.__class__.__name__, dataset.id ) )
            JSONified_dict = json.load( open( filename ) )
        elif json_dict is not None:
            log.debug( 'loading metadata from dict for: %s %s' % ( dataset.__class__.__name__, dataset.id ) )
            if isinstance( json_dict, basestring ):
                JSONified_dict = json.loads( json_dict )
            elif isinstance( json_dict, dict ):
                JSONified_dict = json_dict
            else:
                raise ValueError( "json_dict must be either a dictionary or a string, got %s."  % ( type( json_dict ) ) )
        else:
            raise ValueError( "You must provide either a filename or a json_dict" )
        for name, spec in self.spec.items():
            if name in JSONified_dict:
                from_ext_kwds = {}
                external_value = JSONified_dict[ name ]
                param = spec.param
                if isinstance( param, FileParameter ):
                    from_ext_kwds[ 'path_rewriter' ] = path_rewriter
                dataset._metadata[ name ] = param.from_external_value( external_value, dataset, **from_ext_kwds )
            elif name in dataset._metadata:
                #if the metadata value is not found in our externally set metadata but it has a value in the 'old'
                #metadata associated with our dataset, we'll delete it from our dataset's metadata dict
                del dataset._metadata[ name ]

    def to_JSON_dict( self, filename=None ):
        #galaxy.model.customtypes.json_encoder.encode()
        meta_dict = {}
        dataset_meta_dict = self.parent._metadata
        for name, spec in self.spec.items():
            if name in dataset_meta_dict:
                meta_dict[ name ] = spec.param.to_external_value( dataset_meta_dict[ name ] )
        if filename is None:
            return json.dumps( meta_dict )
        json.dump( meta_dict, open( filename, 'wb+' ) )

    def __getstate__( self ):
        return None #cannot pickle a weakref item (self._parent), when data._metadata_collection is None, it will be recreated on demand


class MetadataSpecCollection( odict ):
    """
    A simple extension of dict which allows cleaner access to items
    and allows the values to be iterated over directly as if it were a
    list.  append() is also implemented for simplicity and does not
    "append".
    """
    def __init__( self, dict = None ):
        odict.__init__( self, dict = None )

    def append( self, item ):
        self[item.name] = item

    def iter( self ):
        return self.itervalues()

    def __getattr__( self, name ):
        return self.get( name )

    def __repr__( self ):
        # force elements to draw with __str__ for sphinx-apidoc
        return ', '.join([ item.__str__() for item in self.iter() ])


class MetadataParameter( object ):
    def __init__( self, spec ):
        self.spec = spec

    def get_html_field( self, value=None, context=None, other_values=None, **kwd ):
        context = context or {}
        other_values = other_values or {}
        return form_builder.TextField( self.spec.name, value=value )

    def get_html( self, value, context=None, other_values=None, **kwd ):
        """
        The "context" is simply the metadata collection/bunch holding
        this piece of metadata. This is passed in to allow for
        metadata to validate against each other (note: this could turn
        into a huge, recursive mess if not done with care). For
        example, a column assignment should validate against the
        number of columns in the dataset.
        """
        context = context or {}
        other_values = other_values or {}

        if self.spec.get("readonly"):
            return value
        if self.spec.get("optional"):
            checked = False
            if value: checked = "true"
            checkbox = form_builder.CheckboxField( "is_" + self.spec.name, checked=checked )
            return checkbox.get_html() + self.get_html_field( value=value, context=context, other_values=other_values, **kwd ).get_html()
        else:
            return self.get_html_field( value=value, context=context, other_values=other_values, **kwd ).get_html()

    def to_string( self, value ):
        return str( value )

    def make_copy( self, value, target_context = None, source_context = None ):
        return copy.deepcopy( value )

    @classmethod
    def marshal ( cls, value ):
        """
        This method should/can be overridden to convert the incoming
        value to whatever type it is supposed to be.
        """
        return value

    def validate( self, value ):
        """
        Throw an exception if the value is invalid.
        """
        pass

    def unwrap( self, form_value ):
        """
        Turns a value into its storable form.
        """
        value = self.marshal( form_value )
        self.validate( value )
        return value

    def wrap( self, value, session ):
        """
        Turns a value into its usable form.
        """
        return value

    def from_external_value( self, value, parent ):
        """
        Turns a value read from an external dict into its value to be pushed directly into the metadata dict.
        """
        return value

    def to_external_value( self, value ):
        """
        Turns a value read from a metadata into its value to be pushed directly into the external dict.
        """
        return value


class MetadataElementSpec( object ):
    """
    Defines a metadata element and adds it to the metadata_spec (which
    is a MetadataSpecCollection) of datatype.
    """
    def __init__( self, datatype,
                  name=None, desc=None, param=MetadataParameter, default=None, no_value = None,
                  visible=True, set_in_upload = False, **kwargs ):
        self.name = name
        self.desc = desc or name
        self.default = default
        self.no_value = no_value
        self.visible = visible
        self.set_in_upload = set_in_upload
        # Catch-all, allows for extra attributes to be set
        self.__dict__.update(kwargs)
        # set up param last, as it uses values set above
        self.param = param( self )
        # add spec element to the spec
        datatype.metadata_spec.append( self )

    def get( self, name, default=None ):
        return self.__dict__.get(name, default)

    def wrap( self, value, session ):
        """
        Turns a stored value into its usable form.
        """
        return self.param.wrap( value, session )

    def unwrap( self, value ):
        """
        Turns an incoming value into its storable form.
        """
        return self.param.unwrap( value )

    def __str__( self ):
        #TODO??: assuming param is the class of this MetadataElementSpec - add the plain class name for that
        spec_dict = dict( param_class=self.param.__class__.__name__ )
        spec_dict.update( self.__dict__ )
        return ( "{name} ({param_class}): {desc}, defaults to '{default}'".format( **spec_dict ) )

# create a statement class that, when called,
#   will add a new MetadataElementSpec to a class's metadata_spec
MetadataElement = Statement( MetadataElementSpec )


"""
MetadataParameter sub-classes.
"""

class SelectParameter( MetadataParameter ):
    def __init__( self, spec ):
        MetadataParameter.__init__( self, spec )
        self.values = self.spec.get( "values" )
        self.multiple = string_as_bool( self.spec.get( "multiple" ) )

    def to_string( self, value ):
        if value in [ None, [] ]:
            return str( self.spec.no_value )
        if not isinstance( value, list ):
            value = [value]
        return ",".join( map( str, value ) )

    def get_html_field( self, value=None, context=None, other_values=None, values=None, **kwd ):
        context = context or {}
        other_values = other_values or {}

        field = form_builder.SelectField( self.spec.name, multiple=self.multiple, display=self.spec.get("display") )
        if self.values:
            value_list = self.values
        elif values:
            value_list = values
        elif value:
            value_list = [ ( v, v ) for v in listify( value )]
        else:
            value_list = []
        for val, label in value_list:
            try:
                if ( self.multiple and val in value ) or ( not self.multiple and val == value ):
                    field.add_option( label, val, selected=True )
                else:
                    field.add_option( label, val, selected=False )
            except TypeError:
                field.add_option( val, label, selected=False )
        return field

    def get_html( self, value, context=None, other_values=None, values=None, **kwd ):
        context = context or {}
        other_values = other_values or {}

        if self.spec.get("readonly"):
            if value in [ None, [] ]:
                return str( self.spec.no_value )
            return ", ".join( map( str, value ) )
        return MetadataParameter.get_html( self, value, context=context, other_values=other_values, values=values, **kwd )

    def wrap( self, value, session ):
        value = self.marshal( value ) #do we really need this (wasteful)? - yes because we are not sure that all existing selects have been stored previously as lists. Also this will handle the case where defaults/no_values are specified and are single non-list values.
        if self.multiple:
            return value
        elif value:
            return value[0] #single select, only return the first value
        return None

    @classmethod
    def marshal( cls, value ):
        # Store select as list, even if single item
        if value is None: return []
        if not isinstance( value, list ): return [value]
        return value


class DBKeyParameter( SelectParameter ):

    def get_html_field( self, value=None, context=None, other_values=None, values=None, **kwd):
        context = context or {}
        other_values = other_values or {}
        try:
            values = kwd['trans'].app.genome_builds.get_genome_build_names( kwd['trans'] )
        except KeyError:
            pass
        return super(DBKeyParameter, self).get_html_field( value, context, other_values, values, **kwd)

    def get_html( self, value=None, context=None, other_values=None, values=None, **kwd):
        context = context or {}
        other_values = other_values or {}
        try:
            values = kwd['trans'].app.genome_builds.get_genome_build_names( kwd['trans'] )
        except KeyError:
            pass
        return super(DBKeyParameter, self).get_html( value, context, other_values, values, **kwd)


class RangeParameter( SelectParameter ):

    def __init__( self, spec ):
        SelectParameter.__init__( self, spec )
        # The spec must be set with min and max values
        self.min = spec.get( "min" ) or 1
        self.max = spec.get( "max" ) or 1
        self.step = self.spec.get( "step" ) or 1

    def get_html_field( self, value=None, context=None, other_values=None, values=None, **kwd ):
        context = context or {}
        other_values = other_values or {}

        if values is None:
            values = zip( range( self.min, self.max, self.step ), range( self.min, self.max, self.step ))
        return SelectParameter.get_html_field( self, value=value, context=context, other_values=other_values, values=values, **kwd )

    def get_html( self, value, context=None, other_values=None, values=None, **kwd ):
        context = context or {}
        other_values = other_values or {}

        if values is None:
            values = zip( range( self.min, self.max, self.step ), range( self.min, self.max, self.step ))
        return SelectParameter.get_html( self, value, context=context, other_values=other_values, values=values, **kwd )

    @classmethod
    def marshal( cls, value ):
        value = SelectParameter.marshal( value )
        values = [ int(x) for x in value ]
        return values


class ColumnParameter( RangeParameter ):

    def get_html_field( self, value=None, context=None, other_values=None, values=None, **kwd ):
        context = context or {}
        other_values = other_values or {}

        if values is None and context:
            column_range = range( 1, ( context.columns or 0 ) + 1, 1 )
            values = zip( column_range, column_range )
        return RangeParameter.get_html_field( self, value=value, context=context, other_values=other_values, values=values, **kwd )

    def get_html( self, value, context=None, other_values=None, values=None, **kwd ):
        context = context or {}
        other_values = other_values or {}

        if values is None and context:
            column_range = range( 1, ( context.columns or 0 ) + 1, 1 )
            values = zip( column_range, column_range )
        return RangeParameter.get_html( self, value, context=context, other_values=other_values, values=values, **kwd )


class ColumnTypesParameter( MetadataParameter ):

    def to_string( self, value ):
        return ",".join( map( str, value ) )


class ListParameter( MetadataParameter ):

    def to_string( self, value ):
        return ",".join( [str(x) for x in value] )


class DictParameter( MetadataParameter ):

    def to_string( self, value ):
        return  json.dumps( value )


class PythonObjectParameter( MetadataParameter ):

    def to_string( self, value ):
        if not value:
            return self.spec._to_string( self.spec.no_value )
        return self.spec._to_string( value )

    def get_html_field( self, value=None, context=None, other_values=None, **kwd ):
        context = context or {}
        other_values = other_values or {}
        return form_builder.TextField( self.spec.name, value=self._to_string( value ) )

    def get_html( self, value=None, context=None, other_values=None, **kwd ):
        context = context or {}
        other_values = other_values or {}
        return str( self )

    @classmethod
    def marshal( cls, value ):
        return value


class FileParameter( MetadataParameter ):

    def to_string( self, value ):
        if not value:
            return str( self.spec.no_value )
        return value.file_name

    def get_html_field( self, value=None, context=None, other_values=None, **kwd ):
        context = context or {}
        other_values = other_values or {}
        return form_builder.TextField( self.spec.name, value=str( value.id ) )

    def get_html( self, value=None, context=None, other_values=None, **kwd ):
        context = context or {}
        other_values = other_values or {}
        return "<div>No display available for Metadata Files</div>"

    def wrap( self, value, session ):
        if value is None:
            return None
        if isinstance( value, galaxy.model.MetadataFile ) or isinstance( value, MetadataTempFile ):
            return value
        mf = session.query( galaxy.model.MetadataFile ).get( value )
        return mf

    def make_copy( self, value, target_context, source_context ):
        value = self.wrap( value, object_session( target_context.parent ) )
        if value:
            new_value = galaxy.model.MetadataFile( dataset = target_context.parent, name = self.spec.name )
            object_session( target_context.parent ).add( new_value )
            object_session( target_context.parent ).flush()
            shutil.copy( value.file_name, new_value.file_name )
            return self.unwrap( new_value )
        return None

    @classmethod
    def marshal( cls, value ):
        if isinstance( value, galaxy.model.MetadataFile ):
            value = value.id
        return value

    def from_external_value( self, value, parent, path_rewriter=None ):
        """
        Turns a value read from a external dict into its value to be pushed directly into the metadata dict.
        """
        if MetadataTempFile.is_JSONified_value( value ):
            value = MetadataTempFile.from_JSON( value )
        if isinstance( value, MetadataTempFile ):
            mf = parent.metadata.get( self.spec.name, None)
            if mf is None:
                mf = self.new_file( dataset = parent, **value.kwds )
            # Ensure the metadata file gets updated with content
            file_name = value.file_name
            if path_rewriter:
                # Job may have run with a different (non-local) tmp/working
                # directory. Correct.
                file_name = path_rewriter( file_name )
            parent.dataset.object_store.update_from_file( mf, file_name=file_name, extra_dir='_metadata_files', extra_dir_at_root=True, alt_name=os.path.basename(mf.file_name) )
            os.unlink( file_name )
            value = mf.id
        return value

    def to_external_value( self, value ):
        """
        Turns a value read from a metadata into its value to be pushed directly into the external dict.
        """
        if isinstance( value, galaxy.model.MetadataFile ):
            value = value.id
        elif isinstance( value, MetadataTempFile ):
            value = MetadataTempFile.to_JSON( value )
        return value

    def new_file( self, dataset = None, **kwds ):
        if object_session( dataset ):
            mf = galaxy.model.MetadataFile( name = self.spec.name, dataset = dataset, **kwds )
            object_session( dataset ).add( mf )
            object_session( dataset ).flush() #flush to assign id
            return mf
        else:
            #we need to make a tmp file that is accessable to the head node,
            #we will be copying its contents into the MetadataFile objects filename after restoring from JSON
            #we do not include 'dataset' in the kwds passed, as from_JSON_value() will handle this for us
            return MetadataTempFile( **kwds )


#This class is used when a database file connection is not available
class MetadataTempFile( object ):
    tmp_dir = 'database/tmp' #this should be overwritten as necessary in calling scripts

    def __init__( self, **kwds ):
        self.kwds = kwds
        self._filename = None

    @property
    def file_name( self ):
        if self._filename is None:
            #we need to create a tmp file, accessable across all nodes/heads, save the name, and return it
            self._filename = abspath( tempfile.NamedTemporaryFile( dir = self.tmp_dir, prefix = "metadata_temp_file_" ).name )
            open( self._filename, 'wb+' ) #create an empty file, so it can't be reused using tempfile
        return self._filename

    def to_JSON( self ):
        return { '__class__':self.__class__.__name__, 'filename':self.file_name, 'kwds':self.kwds }

    @classmethod
    def from_JSON( cls, json_dict ):
        #need to ensure our keywords are not unicode
        rval = cls( **stringify_dictionary_keys( json_dict['kwds'] ) )
        rval._filename = json_dict['filename']
        return rval

    @classmethod
    def is_JSONified_value( cls, value ):
        return ( isinstance( value, dict ) and value.get( '__class__', None ) == cls.__name__ )

    @classmethod
    def cleanup_from_JSON_dict_filename( cls, filename ):
        try:
            for key, value in json.load( open( filename ) ).items():
                if cls.is_JSONified_value( value ):
                    value = cls.from_JSON( value )
                if isinstance( value, cls ) and os.path.exists( value.file_name ):
                    log.debug( 'Cleaning up abandoned MetadataTempFile file: %s' % value.file_name )
                    os.unlink( value.file_name )
        except Exception, e:
            log.debug( 'Failed to cleanup MetadataTempFile temp files from %s: %s' % ( filename, e ) )


#Class with methods allowing set_meta() to be called externally to the Galaxy head
class JobExternalOutputMetadataWrapper( object ):
    #this class allows access to external metadata filenames for all outputs associated with a job
    #We will use JSON as the medium of exchange of information, except for the DatasetInstance object which will use pickle (in the future this could be JSONified as well)

    def __init__( self, job ):
        self.job_id = job.id

    def get_output_filenames_by_dataset( self, dataset, sa_session ):
        if isinstance( dataset, galaxy.model.HistoryDatasetAssociation ):
            return sa_session.query( galaxy.model.JobExternalOutputMetadata ) \
                             .filter_by( job_id = self.job_id, history_dataset_association_id = dataset.id ) \
                             .first() #there should only be one or None
        elif isinstance( dataset, galaxy.model.LibraryDatasetDatasetAssociation ):
            return sa_session.query( galaxy.model.JobExternalOutputMetadata ) \
                             .filter_by( job_id = self.job_id, library_dataset_dataset_association_id = dataset.id ) \
                             .first() #there should only be one or None
        return None

    def get_dataset_metadata_key( self, dataset ):
        # Set meta can be called on library items and history items,
        # need to make different keys for them, since ids can overlap
        return "%s_%d" % ( dataset.__class__.__name__, dataset.id )

    def setup_external_metadata( self, datasets, sa_session, exec_dir=None, tmp_dir=None, dataset_files_path=None,
                                 output_fnames=None, config_root=None, config_file=None, datatypes_config=None, job_metadata=None, compute_tmp_dir=None, kwds=None ):
        kwds = kwds or {}
        if tmp_dir is None:
            tmp_dir = MetadataTempFile.tmp_dir

        # path is calculated for Galaxy, may be different on compute - rewrite
        # for the compute server.
        def metadata_path_on_compute(path):
            compute_path = path
            if compute_tmp_dir and tmp_dir and in_directory(path, tmp_dir):
                path_relative = os.path.relpath(path, tmp_dir)
                compute_path = os.path.join(compute_tmp_dir, path_relative)
            return compute_path

        #fill in metadata_files_dict and return the command with args required to set metadata
        def __metadata_files_list_to_cmd_line( metadata_files ):
            def __get_filename_override():
                if output_fnames:
                    for dataset_path in output_fnames:
                        if dataset_path.false_path and dataset_path.real_path == metadata_files.dataset.file_name:
                            return dataset_path.false_path
                return ""
            line = "%s,%s,%s,%s,%s,%s" % (
                metadata_path_on_compute(metadata_files.filename_in),
                metadata_path_on_compute(metadata_files.filename_kwds),
                metadata_path_on_compute(metadata_files.filename_out),
                metadata_path_on_compute(metadata_files.filename_results_code),
                __get_filename_override(),
                metadata_path_on_compute(metadata_files.filename_override_metadata),
            )
            return line
        if not isinstance( datasets, list ):
            datasets = [ datasets ]
        if exec_dir is None:
            exec_dir = os.path.abspath( os.getcwd() )
        if dataset_files_path is None:
            dataset_files_path = galaxy.model.Dataset.file_path
        if config_root is None:
            config_root = os.path.abspath( os.getcwd() )
        if datatypes_config is None:
            raise Exception( 'In setup_external_metadata, the received datatypes_config is None.' )
            datatypes_config = 'datatypes_conf.xml'
        metadata_files_list = []
        for dataset in datasets:
            key = self.get_dataset_metadata_key( dataset )
            #future note:
            #wonkiness in job execution causes build command line to be called more than once
            #when setting metadata externally, via 'auto-detect' button in edit attributes, etc.,
            #we don't want to overwrite (losing the ability to cleanup) our existing dataset keys and files,
            #so we will only populate the dictionary once
            metadata_files = self.get_output_filenames_by_dataset( dataset, sa_session )
            if not metadata_files:
                metadata_files = galaxy.model.JobExternalOutputMetadata( dataset = dataset)
                metadata_files.job_id = self.job_id
                #we are using tempfile to create unique filenames, tempfile always returns an absolute path
                #we will use pathnames relative to the galaxy root, to accommodate instances where the galaxy root
                #is located differently, i.e. on a cluster node with a different filesystem structure

                #file to store existing dataset
                metadata_files.filename_in = abspath( tempfile.NamedTemporaryFile( dir = tmp_dir, prefix = "metadata_in_%s_" % key ).name )

                #FIXME: HACK
                #sqlalchemy introduced 'expire_on_commit' flag for sessionmaker at version 0.5x
                #This may be causing the dataset attribute of the dataset_association object to no-longer be loaded into memory when needed for pickling.
                #For now, we'll simply 'touch' dataset_association.dataset to force it back into memory.
                dataset.dataset #force dataset_association.dataset to be loaded before pickling
                #A better fix could be setting 'expire_on_commit=False' on the session, or modifying where commits occur, or ?

                cPickle.dump( dataset, open( metadata_files.filename_in, 'wb+' ) )
                #file to store metadata results of set_meta()
                metadata_files.filename_out = abspath( tempfile.NamedTemporaryFile( dir = tmp_dir, prefix = "metadata_out_%s_" % key ).name )
                open( metadata_files.filename_out, 'wb+' ) # create the file on disk, so it cannot be reused by tempfile (unlikely, but possible)
                #file to store a 'return code' indicating the results of the set_meta() call
                #results code is like (True/False - if setting metadata was successful/failed , exception or string of reason of success/failure )
                metadata_files.filename_results_code = abspath( tempfile.NamedTemporaryFile( dir = tmp_dir, prefix = "metadata_results_%s_" % key ).name )
                json.dump( ( False, 'External set_meta() not called' ), open( metadata_files.filename_results_code, 'wb+' ) ) # create the file on disk, so it cannot be reused by tempfile (unlikely, but possible)
                #file to store kwds passed to set_meta()
                metadata_files.filename_kwds = abspath( tempfile.NamedTemporaryFile( dir = tmp_dir, prefix = "metadata_kwds_%s_" % key ).name )
                json.dump( kwds, open( metadata_files.filename_kwds, 'wb+' ), ensure_ascii=True )
                #existing metadata file parameters need to be overridden with cluster-writable file locations
                metadata_files.filename_override_metadata = abspath( tempfile.NamedTemporaryFile( dir = tmp_dir, prefix = "metadata_override_%s_" % key ).name )
                open( metadata_files.filename_override_metadata, 'wb+' ) # create the file on disk, so it cannot be reused by tempfile (unlikely, but possible)
                override_metadata = []
                for meta_key, spec_value in dataset.metadata.spec.iteritems():
                    if isinstance( spec_value.param, FileParameter ) and dataset.metadata.get( meta_key, None ) is not None:
                        metadata_temp = MetadataTempFile()
                        shutil.copy( dataset.metadata.get( meta_key, None ).file_name, metadata_temp.file_name )
                        override_metadata.append( ( meta_key, metadata_temp.to_JSON() ) )
                json.dump( override_metadata, open( metadata_files.filename_override_metadata, 'wb+' ) )
                #add to session and flush
                sa_session.add( metadata_files )
                sa_session.flush()
            metadata_files_list.append( metadata_files )
        #return command required to build
        return "%s %s %s %s %s %s %s %s" % ( os.path.join( exec_dir, 'set_metadata.sh' ), dataset_files_path, compute_tmp_dir or tmp_dir, config_root, config_file, datatypes_config, job_metadata, " ".join( map( __metadata_files_list_to_cmd_line, metadata_files_list ) ) )

    def external_metadata_set_successfully( self, dataset, sa_session ):
        metadata_files = self.get_output_filenames_by_dataset( dataset, sa_session )
        if not metadata_files:
            return False # this file doesn't exist
        rval, rstring = json.load( open( metadata_files.filename_results_code ) )
        if not rval:
            log.debug( 'setting metadata externally failed for %s %s: %s' % ( dataset.__class__.__name__, dataset.id, rstring ) )
        return rval

    def cleanup_external_metadata( self, sa_session ):
        log.debug( 'Cleaning up external metadata files' )
        for metadata_files in sa_session.query( galaxy.model.Job ).get( self.job_id ).external_output_metadata:
            #we need to confirm that any MetadataTempFile files were removed, if not we need to remove them
            #can occur if the job was stopped before completion, but a MetadataTempFile is used in the set_meta
            MetadataTempFile.cleanup_from_JSON_dict_filename( metadata_files.filename_out )
            dataset_key = self.get_dataset_metadata_key( metadata_files.dataset )
            for key, fname in [ ( 'filename_in', metadata_files.filename_in ), ( 'filename_out', metadata_files.filename_out ), ( 'filename_results_code', metadata_files.filename_results_code ), ( 'filename_kwds', metadata_files.filename_kwds ), ( 'filename_override_metadata', metadata_files.filename_override_metadata ) ]:
                try:
                    os.remove( fname )
                except Exception, e:
                    log.debug( 'Failed to cleanup external metadata file (%s) for %s: %s' % ( key, dataset_key, e ) )

    def set_job_runner_external_pid( self, pid, sa_session ):
        for metadata_files in sa_session.query( galaxy.model.Job ).get( self.job_id ).external_output_metadata:
            metadata_files.job_runner_external_pid = pid
            sa_session.add( metadata_files )
            sa_session.flush()
