"""
Support for generating the options for a SelectToolParameter dynamically (based
on the values of other parameters or other aspects of the current state)
"""

import operator, sys, os, logging
import basic, validation
from galaxy.util import string_as_bool

log = logging.getLogger(__name__)

class Filter( object ):
    """
    A filter takes the current options list and modifies it.
    """
    @classmethod
    def from_element( cls, d_option, elem ):
        """Loads the proper filter by the type attribute of elem"""
        type = elem.get( 'type', None )
        assert type is not None, "Required 'type' attribute missing from filter"
        return filter_types[type.strip()]( d_option, elem )
    def __init__( self, d_option, elem ):
        self.dynamic_option = d_option
        self.elem = elem
    def get_dependency_name( self ):
        """Returns the name of any depedencies, otherwise None"""
        return None
    def filter_options( self, trans, other_values ):
        """Returns a list of options after the filter is applied"""
        raise TypeError( "Abstract Method" )

class StaticValueFilter( Filter ):
    """
    Filters a list of options on a column by a static value.
    
    Type: static_value
    
    Required Attributes:
        value: static value to compare to
        column: column in options to compare with
    Optional Attributes:
        keep: Keep columns matching value (True)
              Discard columns matching value (False)
    """
    def __init__( self, d_option, elem ):
        Filter.__init__( self, d_option, elem )
        self.value = elem.get( "value", None )
        assert self.value is not None, "Required 'value' attribute missing from filter"
        self.column = elem.get( "column", None )
        assert self.column is not None, "Required 'column' attribute missing from filter, when loading from file"
        self.column = int ( self.column )
        self.keep = string_as_bool( elem.get( "keep", 'True' ) )
    def filter_options( self, options, trans, other_values ):
        rval = []
        for fields in options:
            if ( self.keep and fields[self.column] == self.value ) or ( not self.keep and fields[self.column] != self.value ):
                rval.append( fields )
        return rval

class DataMetaFilter( Filter ):
    """
    Filters a list of options on a column by a dataset metadata value.
    
    Type: data_meta
    
    When no 'from_' source has been specified in the <options> tag, this will populate the options list with (meta_value, meta_value, False).
    Otherwise, options which do not match the metadata value in the column are discarded.
    
    Required Attributes:
        ref: Name of input dataset
        key: Metadata key to use for comparison
        column: column in options to compare with (not required when not associated with input options)
    Optional Attributes:
        multiple: Option values are multiple, split column by separator (True)
        separator: When multiple split by this (,)
    """
    def __init__( self, d_option, elem ):
        Filter.__init__( self, d_option, elem )
        self.ref_name = elem.get( "ref", None )
        assert self.ref_name is not None, "Required 'ref' attribute missing from filter"
        self.key = elem.get( "key", None )
        assert self.key is not None, "Required 'key' attribute missing from filter"
        self.column = elem.get( "column", None )
        if self.column is None:
            assert self.dynamic_option.file_fields is None and self.dynamic_option.dataset_ref_name is None, "Required 'column' attribute missing from filter, when loading from file"
        else:
            self.column = int ( self.column )
        self.multiple = string_as_bool( elem.get( "multiple", "False" ) )
        self.separator = elem.get( "separator", "," )
    def get_dependency_name( self ):
        return self.ref_name
    def filter_options( self, options, trans, other_values ):
        def compare_meta_value( file_value, dataset_value ):
            if isinstance( dataset_value, list ):
                if self.multiple:
                    file_value = file_value.split( self.separator )
                    for value in dataset_value:
                        if value not in file_value:
                            return False
                    return True
                return file_value in dataset_value
            if self.multiple:
                return dataset_value in file_value.split( self.separator )
            return file_value == dataset_value
        ref = other_values.get( self.ref_name, None )
        assert ref is not None, "Required dependency '%s' not found in incoming values" % ref
        if not isinstance( ref, self.dynamic_option.tool_param.tool.app.model.Dataset ):
            return [] #not a valid dataset
        meta_value = ref.metadata.get( self.key, None )
        assert meta_value is not None, "Required metadata value '%s' not found in referenced dataset" % self.key
        
        if self.column is not None:
            rval = []
            for fields in options:
                if compare_meta_value( fields[self.column], meta_value ):
                    rval.append( fields )
            return rval
        else:
            if not isinstance( meta_value, list ):
                meta_value = [meta_value]
            for value in meta_value:
                options.append( ( value, value, False ) )
            return options

class ParamValueFilter( Filter ):
    """
    Filters a list of options on a column by the value of another input.
    
    Type: param_value
    
    Required Attributes:
        ref: Name of input value
        column: column in options to compare with
    Optional Attributes:
        keep: Keep columns matching value (True)
              Discard columns matching value (False)
    """
    def __init__( self, d_option, elem ):
        Filter.__init__( self, d_option, elem )
        self.ref_name = elem.get( "ref", None )
        assert self.ref_name is not None, "Required 'ref' attribute missing from filter"
        self.column = elem.get( "column", None )
        assert self.column is not None, "Required 'column' attribute missing from filter"
        self.column = int ( self.column )
        self.keep = string_as_bool( elem.get( "keep", 'True' ) )
    def get_dependency_name( self ):
        return self.ref_name
    def filter_options( self, options, trans, other_values ):
        ref = str( other_values.get( self.ref_name, None ) )
        assert ref is not None, "Required dependency '%s' not found in incoming values" % ref
        rval = []
        for fields in options:
            if ( self.keep and fields[self.column] == ref ) or ( not self.keep and fields[self.column] != ref ):
                rval.append( fields )
        return rval

class UniqueValueFilter( Filter ):
    """
    Filters a list of options to be unique by a column value.
    
    Type: unique_value
    
    Required Attributes:
        column: column in options to compare with
    """
    def __init__( self, d_option, elem ):
        Filter.__init__( self, d_option, elem )
        self.column = elem.get( "column", None )
        assert self.column is not None, "Required 'column' attribute missing from filter"
        self.column = int ( self.column )
    def get_dependency_name( self ):
        return self.dynamic_option.dataset_ref_name
    def filter_options( self, options, trans, other_values ):
        rval = []
        skip_list = []
        for fields in options:
            if fields[self.column] not in skip_list:
                rval.append( fields )
                skip_list.append( fields[self.column] )
        return rval

class MultipleSplitterFilter( Filter ):
    """
    Turns a single line of options into multiple lines, by splitting a column and creating a line for each item.
    
    Type: multiple_splitter
    
    Required Attributes:
        column: column in options to compare with
    Optional Attributes:
        separator: Split column by this (,)
    """
    def __init__( self, d_option, elem ):
        Filter.__init__( self, d_option, elem )
        self.separator = elem.get( "separator", "," )
        self.columns = elem.get( "column", None )
        assert self.columns is not None, "Required 'columns' attribute missing from filter"
        self.columns = [ int ( column ) for column in self.columns.split( "," ) ]
    def filter_options( self, options, trans, other_values ):
        rval = []
        for fields in options:
            for column in self.columns:
                for field in fields[column].split( self.separator ):
                    rval.append( fields[0:column] + [field] + fields[column:] )
        return rval

class AdditionalValueFilter( Filter ):
    """
    Adds a single static value to an options list.
    
    Type: add_value
    
    Required Attributes:
        value: value to appear in select list
    Optional Attributes:
        name: Display name to appear in select list (value)
        index: Index of option list to add value (APPEND)
    """
    def __init__( self, d_option, elem ):
        Filter.__init__( self, d_option, elem )
        self.value = elem.get( "value", None )
        assert self.value is not None, "Required 'value' attribute missing from filter"
        self.name = elem.get( "name", None )
        if self.name is None:
            self.name = self.value
        self.index = elem.get( "index", None )
        if self.index is not None:
            self.index = int( self.index )
    def filter_options( self, options, trans, other_values ):
        rval = list( options )
        add_value = []
        for i in range( self.dynamic_option.largest_index + 1 ):
            add_value.append( "" )
        add_value[self.dynamic_option.columns['value']] = self.value
        add_value[self.dynamic_option.columns['name']] = self.name
        if self.index is not None:
            rval.insert( self.index, add_value )
        else:
            rval.append( add_value )
        return rval

class SortByColumnFilter( Filter ):
    """
    Sorts an options list by a column
    
    Type: sort_by
    
    Required Attributes:
        column: column to sort by
    """
    def __init__( self, d_option, elem ):
        Filter.__init__( self, d_option, elem )
        self.column = elem.get( "column", None )
        assert self.column is not None, "Required 'column' attribute missing from filter"
        self.column = int( self.column )
    def filter_options( self, options, trans, other_values ):
        rval = []
        for i, fields in enumerate( options ):
            for j in range( 0, len( rval ) ):
                if fields[self.column] < rval[j][self.column]:
                    rval.insert( j, fields )
                    break
            else:
                rval.append( fields )
        return rval


filter_types = dict( data_meta = DataMetaFilter,
                     param_value = ParamValueFilter,
                     static_value = StaticValueFilter,
                     unique_value = UniqueValueFilter,
                     multiple_splitter = MultipleSplitterFilter,
                     add_value = AdditionalValueFilter,
                     sort_by = SortByColumnFilter )

class DynamicOptions( object ):
    """Handles dynamically generated SelectToolParameter options"""
    def __init__( self, elem, tool_param  ):
        def load_from_parameter( from_parameter, transform_lines = None ):
            obj = self.tool_param
            for field in from_parameter.split( '.' ):
                obj = getattr( obj, field )
            if transform_lines:
                obj = eval( transform_lines )
            return self.parse_file_fields( obj )
        self.tool_param = tool_param
        self.columns = {}
        self.filters = []
        self.file_fields = None
        self.largest_index = 0
        self.dataset_ref_name = None
        self.validators = []
        
        # Parse the <options> tag
        self.separator = elem.get( 'separator', '\t' )
        self.line_startswith = elem.get( 'startswith', None )
        data_file = elem.get( 'from_file', None )
        dataset_file = elem.get( 'from_dataset', None )
        from_parameter = elem.get( 'from_parameter', None )
        if data_file is not None or dataset_file is not None or from_parameter is not None:
            for column_elem in elem.findall( 'column' ):
                name = column_elem.get( 'name', None )
                assert name is not None, "Required 'name' attribute missing from column def"
                index = column_elem.get( 'index', None )
                assert index is not None, "Required 'index' attribute missing from column def"
                index = int( index )
                self.columns[name] = index
                if index > self.largest_index:
                    self.largest_index = index
            assert 'value' in self.columns, "Required 'value' column missing from column def"
            if 'name' not in self.columns:
                self.columns['name'] = self.columns['value']
            
            if data_file is not None:
                data_file = data_file.strip()
                if not os.path.isabs( data_file ):
                    data_file = os.path.join( self.tool_param.tool.app.config.tool_data_path, data_file )
                self.file_fields = self.parse_file_fields( open( data_file ) )
            elif dataset_file is not None:
                self.dataset_ref_name = dataset_file
            elif from_parameter is not None:
                transform_lines = elem.get( 'transform_lines', None )
                self.file_fields = list( load_from_parameter( from_parameter, transform_lines ) )
        # Load filters
        for filter_elem in elem.findall( 'filter' ):
            self.filters.append( Filter.from_element( self, filter_elem ) )
        
        # Load Validators
        for validator in elem.findall( 'validator' ):
            validator_type = validator.get( 'type', None )
            assert validator_type is not None, "Required 'type' attribute missing from validator"
            self.validators.append( validation.Validator.from_element( self.tool_param, validator ) )
    
    def parse_file_fields( self, reader ):
        rval = []
        for line in reader:
            if line.startswith( '#' ) or ( self.line_startswith and not line.startswith( self.line_startswith ) ):
                continue
            line = line.rstrip( "\n\r" )
            if line:
                fields = line.split( self.separator )
                if self.largest_index < len( fields ):
                    rval.append( fields )
        return rval
    
    def get_dependency_names( self ):
        """
        Return the names of parameters these options depend on -- both data
        and other param types.
        """
        rval = []
        if self.dataset_ref_name:
            rval.append( self.dataset_ref_name )
        for filter in self.filters:
            depend = filter.get_dependency_name()
            if depend:
                rval.append( depend )
        return rval        
    
    def get_fields( self, trans, other_values ):
        if self.dataset_ref_name:
            dataset = other_values.get( self.dataset_ref_name, None )
            assert dataset is not None, "Required dataset '%s' missing from input" % self.dataset_ref_name
            options = self.parse_file_fields( open( dataset.file_name ) )
        else:
            options = list( self.file_fields )
        for filter in self.filters:
            options = filter.filter_options( options, trans, other_values )
        return options
    
    def get_options( self, trans, other_values ):
        rval = []
        if self.file_fields is not None or self.dataset_ref_name is not None:
            options = self.get_fields( trans, other_values )
            for fields in options:
                rval.append( ( fields[self.columns['name']], fields[self.columns['value']], False ) )
        else:
            for filter in self.filters:
                rval = filter.filter_options( rval, trans, other_values )
        return rval
