import pipes
from galaxy.util.none_like import NoneDataset


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
        def __init__( self, input, value, other_values ):
            self._input = input
            self._value = value
            self._other_values = other_values
            self._fields = {}

        def __getattr__( self, name ):
            if name not in self._fields:
                self._fields[ name ] = self._input.options.get_field_by_name_for_value( name, self._value, None, self._other_values )
            return self._input.separator.join( map( str, self._fields[ name ] ) )

    def __init__( self, input, value, app, other_values={} ):
        self.input = input
        self.value = value
        self.input.value_label = input.value_to_display_text( value, app )
        self._other_values = other_values
        self.fields = self.SelectToolParameterFieldWrapper( input, value, other_values )

    def __str__( self ):
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
        self.false_path = getattr( dataset_path, "false_path", None )
        self.false_extra_files_path = getattr( dataset_path, "false_extra_files_path", None )

    def __str__( self ):
        if self.false_path is not None:
            return self.false_path
        else:
            return self.dataset.file_name

    def __getattr__( self, key ):
        if self.false_path is not None and key == 'file_name':
            return self.false_path
        elif self.false_extra_files_path is not None and key == 'extra_files_path':
            return self.false_extra_files_path
        else:
            return getattr( self.dataset, key )

    def __nonzero__( self ):
        return bool( self.dataset )


class DatasetListWrapper( list ):
    """
    """
    def __init__( self, datasets, dataset_paths=[], **kwargs ):
        if not isinstance(datasets, list):
            datasets = [datasets]

        def to_wrapper( dataset ):
            real_path = dataset.file_name
            wrapper_kwds = kwargs.copy()
            if real_path in dataset_paths:
                wrapper_kwds[ "dataset_path" ] = dataset_paths[ real_path ]
            return DatasetFilenameWrapper( dataset, **wrapper_kwds )

        list.__init__( self, map( to_wrapper, datasets ) )
