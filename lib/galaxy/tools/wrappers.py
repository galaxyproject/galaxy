import pipes
from galaxy import exceptions
from galaxy.util.none_like import NoneDataset
from galaxy.util import odict

from logging import getLogger
log = getLogger( __name__ )

# Fields in .log files corresponding to paths, must have one of the following
# field names and all such fields are assumed to be paths. This is to allow
# remote ComputeEnvironments (such as one used by LWR) determine what values to
# rewrite or transfer...
PATH_ATTRIBUTES = [ "path" ]
# ... by default though - don't rewrite anything (if no ComputeEnviornment
# defined or ComputeEnvironment doesn't supply a rewriter).
DEFAULT_PATH_REWRITER = lambda x: x


class ToolParameterValueWrapper( object ):
    """
    Base class for object that Wraps a Tool Parameter and Value.
    """

    def __nonzero__( self ):
        return bool( self.value )

    def get_display_text( self, quote=True ):
        """
        Returns a string containing the value that would be displayed to the user in the tool interface.
        When quote is True (default), the string is escaped for e.g. command-line usage.
        """
        rval = self.input.value_to_display_text( self.value, self.input.tool.app ) or ''
        if quote:
            return pipes.quote( rval ) or "''"  # pipes.quote in Python < 2.7 returns an empty string instead of the expected quoted empty string
        return rval


class RawObjectWrapper( ToolParameterValueWrapper ):
    """
    Wraps an object so that __str__ returns module_name:class_name.
    """
    def __init__( self, obj ):
        self.obj = obj

    def __nonzero__( self ):
        return bool( self.obj )  # FIXME: would it be safe/backwards compatible to rename .obj to .value, so that we can just inherit this method?

    def __str__( self ):
        try:
            return "%s:%s" % (self.obj.__module__, self.obj.__class__.__name__)
        except:
            #Most likely None, which lacks __module__.
            return str( self.obj )

    def __getattr__( self, key ):
        return getattr( self.obj, key )


class LibraryDatasetValueWrapper( ToolParameterValueWrapper ):
    """
    Wraps an input so that __str__ gives the "param_dict" representation.
    """
    def __init__( self, input, value, other_values={} ):
        self.input = input
        self.value = value
        self._other_values = other_values
        self.counter = 0

    def __str__( self ):
        return self.value

    def __iter__( self ):
        return self

    def next( self ):
        if self.counter >= len(self.value):
            raise StopIteration
        self.counter += 1
        return self.value[ self.counter - 1 ]

    def __getattr__( self, key ):
        return getattr( self.value, key )


class InputValueWrapper( ToolParameterValueWrapper ):
    """
    Wraps an input so that __str__ gives the "param_dict" representation.
    """
    def __init__( self, input, value, other_values={} ):
        self.input = input
        self.value = value
        self._other_values = other_values

    def __str__( self ):
        return self.input.to_param_dict_string( self.value, self._other_values )

    def __getattr__( self, key ):
        return getattr( self.value, key )


class SelectToolParameterWrapper( ToolParameterValueWrapper ):
    """
    Wraps a SelectTooParameter so that __str__ returns the selected value, but all other
    attributes are accessible.
    """

    class SelectToolParameterFieldWrapper:
        """
        Provide access to any field by name or index for this particular value.
        Only applicable for dynamic_options selects, which have more than simple 'options' defined (name, value, selected).
        """
        def __init__( self, input, value, other_values, path_rewriter ):
            self._input = input
            self._value = value
            self._other_values = other_values
            self._fields = {}
            self._path_rewriter = path_rewriter

        def __getattr__( self, name ):
            if name not in self._fields:
                self._fields[ name ] = self._input.options.get_field_by_name_for_value( name, self._value, None, self._other_values )
            values = map( str, self._fields[ name ] )
            if name in PATH_ATTRIBUTES:
                # If we infer this is a path, rewrite it if needed.
                values = map( self._path_rewriter, values )
            return self._input.separator.join( values )

    def __init__( self, input, value, app, other_values={}, path_rewriter=None ):
        self.input = input
        self.value = value
        self.input.value_label = input.value_to_display_text( value, app )
        self._other_values = other_values
        self._path_rewriter = path_rewriter or DEFAULT_PATH_REWRITER
        self.fields = self.SelectToolParameterFieldWrapper( input, value, other_values, self._path_rewriter )

    def __str__( self ):
        # Assuming value is never a path - otherwise would need to pass
        # along following argument value_map=self._path_rewriter.
        return self.input.to_param_dict_string( self.value, other_values=self._other_values )

    def __getattr__( self, key ):
        return getattr( self.input, key )


class DatasetFilenameWrapper( ToolParameterValueWrapper ):
    """
    Wraps a dataset so that __str__ returns the filename, but all other
    attributes are accessible.
    """

    class MetadataWrapper:
        """
        Wraps a Metadata Collection to return MetadataParameters wrapped
        according to the metadata spec. Methods implemented to match behavior
        of a Metadata Collection.
        """
        def __init__( self, metadata ):
            self.metadata = metadata

        def __getattr__( self, name ):
            rval = self.metadata.get( name, None )
            if name in self.metadata.spec:
                if rval is None:
                    rval = self.metadata.spec[name].no_value
                rval = self.metadata.spec[name].param.to_string( rval )
                # Store this value, so we don't need to recalculate if needed
                # again
                setattr( self, name, rval )
            return rval

        def __nonzero__( self ):
            return self.metadata.__nonzero__()

        def __iter__( self ):
            return self.metadata.__iter__()

        def get( self, key, default=None ):
            try:
                return getattr( self, key )
            except:
                return default

        def items( self ):
            return iter( [ ( k, self.get( k ) ) for k, v in self.metadata.items() ] )

    def __init__( self, dataset, datatypes_registry=None, tool=None, name=None, dataset_path=None ):
        if not dataset:
            try:
                # TODO: allow this to work when working with grouping
                ext = tool.inputs[name].extensions[0]
            except:
                ext = 'data'
            self.dataset = NoneDataset( datatypes_registry=datatypes_registry, ext=ext )
        else:
            self.dataset = dataset
            self.metadata = self.MetadataWrapper( dataset.metadata )
        self.datatypes_registry = datatypes_registry
        self.false_path = getattr( dataset_path, "false_path", None )
        self.false_extra_files_path = getattr( dataset_path, "false_extra_files_path", None )

    @property
    def is_collection( self ):
        return False

    def is_of_type( self, *exts ):
        datatypes = [ self.datatypes_registry.get_datatype_by_extension( e ) for e in exts ]
        return self.dataset.datatype.matches_any( datatypes )

    def __str__( self ):
        if self.false_path is not None:
            return self.false_path
        else:
            return self.dataset.file_name

    def __getattr__( self, key ):
        if self.false_path is not None and key == 'file_name':
            # Path to dataset was rewritten for this job.
            return self.false_path
        elif self.false_extra_files_path is not None and key == 'extra_files_path':
            # Path to extra files was rewritten for this job.
            return self.false_extra_files_path
        elif key == 'extra_files_path':
            try:
                # Assume it is an output and that this wrapper
                # will be set with correct "files_path" for this
                # job.
                return self.files_path
            except AttributeError:
                # Otherwise, we have an input - delegate to model and
                # object store to find the static location of this
                # directory.
                try:
                    return self.dataset.extra_files_path
                except exceptions.ObjectNotFound:
                    # NestedObjectstore raises an error here
                    # instead of just returning a non-existent
                    # path like DiskObjectStore.
                    raise
        else:
            return getattr( self.dataset, key )

    def __nonzero__( self ):
        return bool( self.dataset )


class HasDatasets:

    def _dataset_wrapper( self, dataset, dataset_paths, **kwargs ):
        wrapper_kwds = kwargs.copy()
        if dataset:
            real_path = dataset.file_name
            if real_path in dataset_paths:
                wrapper_kwds[ "dataset_path" ] = dataset_paths[ real_path ]
        return DatasetFilenameWrapper( dataset, **wrapper_kwds )


class DatasetListWrapper( list, HasDatasets ):
    """
    """
    def __init__( self, datasets, dataset_paths=[], **kwargs ):
        if not isinstance(datasets, list):
            datasets = [datasets]

        def to_wrapper( dataset ):
            return self._dataset_wrapper( dataset, dataset_paths, **kwargs )

        list.__init__( self, map( to_wrapper, datasets ) )
    def __str__( self ):
        return ','.join( map( str, self ) )


class DatasetCollectionWrapper( object, HasDatasets ):

    def __init__( self, has_collection, dataset_paths=[], **kwargs ):
        super(DatasetCollectionWrapper, self).__init__()

        if has_collection is None:
            self.__input_supplied = False
            return
        else:
            self.__input_supplied = True

        if hasattr( has_collection, "name" ):
            # It is a HistoryDatasetCollectionAssociation
            collection = has_collection.collection
            self.name = has_collection.name
        else:
            # It is a DatasetCollectionElement instance referencing another collection
            collection = has_collection.child_collection
            self.name = has_collection.element_identifier

        elements = collection.elements
        element_instances = odict.odict()

        element_instance_list = []
        for dataset_collection_element in elements:
            element_object = dataset_collection_element.element_object
            element_identifier = dataset_collection_element.element_identifier

            if dataset_collection_element.is_collection:
                element_wrapper = DatasetCollectionWrapper( dataset_collection_element, dataset_paths, **kwargs )
            else:
                element_wrapper = self._dataset_wrapper( element_object, dataset_paths, **kwargs)

            element_instances[element_identifier] = element_wrapper
            element_instance_list.append( element_wrapper )

        self.__element_instances = element_instances
        self.__element_instance_list = element_instance_list

    def keys( self ):
        if not self.__input_supplied:
            return []
        return self.__element_instances.keys()

    @property
    def is_collection( self ):
        return True

    @property
    def is_input_supplied( self ):
        return self.__input_supplied

    def __getitem__( self, key ):
        if not self.__input_supplied:
            return None
        if isinstance( key, int ):
            return self.__element_instance_list[ key ]
        else:
            return self.__element_instances[ key ]

    def __getattr__( self, key ):
        if not self.__input_supplied:
            return None
        return self.__element_instances[ key ]

    def __iter__( self ):
        if not self.__input_supplied:
            return [].__iter__()
        return self.__element_instance_list.__iter__()

    def __nonzero__( self ):
        # Fail `#if $param` checks in cheetah is optional input
        # not specified or if resulting collection is empty.
        return self.__input_supplied and bool( self.__element_instance_list )
