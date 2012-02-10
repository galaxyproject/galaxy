"""
Support for generating the options for a SelectToolParameter dynamically (based
on the values of other parameters or other aspects of the current state)
"""

import operator, sys, os, logging
import basic, validation
from galaxy.util import string_as_bool
import galaxy.tools

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
    def filter_options( self, options, trans, other_values ):
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
        column = elem.get( "column", None )
        assert column is not None, "Required 'column' attribute missing from filter, when loading from file"
        self.column = d_option.column_spec_to_index( column )
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
        d_option.has_dataset_dependencies = True
        self.key = elem.get( "key", None )
        assert self.key is not None, "Required 'key' attribute missing from filter"
        self.column = elem.get( "column", None )
        if self.column is None:
            assert self.dynamic_option.file_fields is None and self.dynamic_option.dataset_ref_name is None, "Required 'column' attribute missing from filter, when loading from file"
        else:
            self.column = d_option.column_spec_to_index( self.column )
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
        assert self.ref_name in other_values or ( trans is not None and trans.workflow_building_mode), "Required dependency '%s' not found in incoming values" % self.ref_name
        ref = other_values.get( self.ref_name, None )
        if not isinstance( ref, self.dynamic_option.tool_param.tool.app.model.HistoryDatasetAssociation ) and not ( isinstance( ref, galaxy.tools.DatasetFilenameWrapper ) ):
            return [] #not a valid dataset
        meta_value = ref.metadata.get( self.key, None )
        if meta_value is None: #assert meta_value is not None, "Required metadata value '%s' not found in referenced dataset" % self.key
            return [ ( disp_name, basic.UnvalidatedValue( optval ), selected ) for disp_name, optval, selected in options ]
        
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
        ref_attribute: Period (.) separated attribute chain of input (ref) to use as value for filter
    """
    def __init__( self, d_option, elem ):
        Filter.__init__( self, d_option, elem )
        self.ref_name = elem.get( "ref", None )
        assert self.ref_name is not None, "Required 'ref' attribute missing from filter"
        column = elem.get( "column", None )
        assert column is not None, "Required 'column' attribute missing from filter"
        self.column = d_option.column_spec_to_index( column )
        self.keep = string_as_bool( elem.get( "keep", 'True' ) )
        self.ref_attribute = elem.get( "ref_attribute", None )
        if self.ref_attribute:
            self.ref_attribute = self.ref_attribute.split( '.' )
        else:
            self.ref_attribute = []
    def get_dependency_name( self ):
        return self.ref_name
    def filter_options( self, options, trans, other_values ):
        if trans is not None and trans.workflow_building_mode: return []
        assert self.ref_name in other_values, "Required dependency '%s' not found in incoming values" % self.ref_name
        ref = other_values.get( self.ref_name, None )
        for ref_attribute in self.ref_attribute:
            if not hasattr( ref, ref_attribute ):
                return [] #ref does not have attribute, so we cannot filter, return empty list
            ref = getattr( ref, ref_attribute )
        ref = str( ref )
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
        column = elem.get( "column", None )
        assert column is not None, "Required 'column' attribute missing from filter"
        self.column = d_option.column_spec_to_index( column )
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
        columns = elem.get( "column", None )
        assert columns is not None, "Required 'columns' attribute missing from filter"
        self.columns = [ d_option.column_spec_to_index( column ) for column in columns.split( "," ) ]
    def filter_options( self, options, trans, other_values ):
        rval = []
        for fields in options:
            for column in self.columns:
                for field in fields[column].split( self.separator ):
                    rval.append( fields[0:column] + [field] + fields[column+1:] )
        return rval
        
class AttributeValueSplitterFilter( Filter ):
    """
    Filters a list of attribute-value pairs to be unique attribute names.

    Type: attribute_value_splitter

    Required Attributes:
        column: column in options to compare with
    Optional Attributes:
        pair_separator: Split column by this (,)
        name_val_separator: Split name-value pair by this ( whitespace )
    """
    def __init__( self, d_option, elem ):
        Filter.__init__( self, d_option, elem )
        self.pair_separator = elem.get( "pair_separator", "," )
        self.name_val_separator = elem.get( "name_val_separator", None )
        self.columns = elem.get( "column", None )
        assert self.columns is not None, "Required 'columns' attribute missing from filter"
        self.columns = [ int ( column ) for column in self.columns.split( "," ) ]
    def filter_options( self, options, trans, other_values ):
        attr_names = []
        rval = []
        for fields in options:
            for column in self.columns:
                for pair in fields[column].split( self.pair_separator ):
                    ary = pair.split( self.name_val_separator )
                    if len( ary ) == 2:
                        name, value = ary
                        if name not in attr_names:
                            rval.append( fields[0:column] + [name] + fields[column:] )
                            attr_names.append( name )
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

class RemoveValueFilter( Filter ):
    """
    Removes a value from an options list.
    
    Type: remove_value
    
    Required Attributes:
        value: value to remove from select list
            or
        ref: param to refer to
            or
        meta_ref: dataset to refer to
        key: metadata key to compare to
    """
    def __init__( self, d_option, elem ):
        Filter.__init__( self, d_option, elem )
        self.value = elem.get( "value", None )
        self.ref_name = elem.get( "ref", None )
        self.meta_ref = elem.get( "meta_ref", None )
        self.metadata_key = elem.get( "key", None )
        assert self.value is not None or ( ( self.ref_name is not None or self.meta_ref is not None )and self.metadata_key is not None ), ValueError( "Required 'value' or 'ref' and 'key' attributes missing from filter" )
        self.multiple = string_as_bool( elem.get( "multiple", "False" ) )
        self.separator = elem.get( "separator", "," )
    def filter_options( self, options, trans, other_values ):
        if trans is not None and trans.workflow_building_mode: return options
        assert self.value is not None or ( self.ref_name is not None and self.ref_name in other_values ) or (self.meta_ref is not None and self.meta_ref in other_values ) or ( trans is not None and trans.workflow_building_mode), Exception( "Required dependency '%s' or '%s' not found in incoming values" % ( self.ref_name, self.meta_ref ) )
        def compare_value( option_value, filter_value ):
            if isinstance( filter_value, list ):
                if self.multiple:
                    option_value = option_value.split( self.separator )
                    for value in filter_value:
                        if value not in filter_value:
                            return False
                    return True
                return option_value in filter_value
            if self.multiple:
                return filter_value in option_value.split( self.separator )
            return option_value == filter_value
        value = self.value
        if value is None:
            if self.ref_name is not None:
                value = other_values.get( self.ref_name )
            else:
                data_ref = other_values.get( self.meta_ref )
                if not isinstance( data_ref, self.dynamic_option.tool_param.tool.app.model.HistoryDatasetAssociation ) and not ( isinstance( data_ref, galaxy.tools.DatasetFilenameWrapper ) ):
                    return options #cannot modify options
                value = data_ref.metadata.get( self.metadata_key, None )
        return [ ( disp_name, optval, selected ) for disp_name, optval, selected in options if not compare_value( optval, value ) ]

class SortByColumnFilter( Filter ):
    """
    Sorts an options list by a column
    
    Type: sort_by
    
    Required Attributes:
        column: column to sort by
    """
    def __init__( self, d_option, elem ):
        Filter.__init__( self, d_option, elem )
        column = elem.get( "column", None )
        assert column is not None, "Required 'column' attribute missing from filter"
        self.column = d_option.column_spec_to_index( column )
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
                     attribute_value_splitter = AttributeValueSplitterFilter,
                     add_value = AdditionalValueFilter,
                     remove_value = RemoveValueFilter,
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
        # True if the options generation depends on one or more other parameters
        # that are dataset inputs
        self.has_dataset_dependencies = False
        self.validators = []
        self.converter_safe = True
        
        # Parse the <options> tag
        self.separator = elem.get( 'separator', '\t' )
        self.line_startswith = elem.get( 'startswith', None )
        data_file = elem.get( 'from_file', None )
        self.index_file = None
        self.missing_index_file = None
        dataset_file = elem.get( 'from_dataset', None )
        from_parameter = elem.get( 'from_parameter', None )
        tool_data_table_name = elem.get( 'from_data_table', None )
        # Options are defined from a data table loaded by the app
        self.tool_data_table = None
        self.missing_tool_data_table_name = None
        if tool_data_table_name:
            app = tool_param.tool.app
            if tool_data_table_name in app.tool_data_tables:
                self.tool_data_table = app.tool_data_tables[ tool_data_table_name ]
                # Column definitions are optional, but if provided override those from the table
                if elem.find( "column" ) is not None:
                    self.parse_column_definitions( elem )
                else:
                    self.columns = self.tool_data_table.columns
                # Set self.missing_index_file if the index file to
                # which the tool_data_table refers does not exist.
                if self.tool_data_table.missing_index_file:
                    self.missing_index_file = self.tool_data_table.missing_index_file
            else:
                self.missing_tool_data_table_name = tool_data_table_name
                log.warn( "Data table named '%s' is required by tool but not configured" % tool_data_table_name )
        # Options are defined by parsing tabular text data from a data file
        # on disk, a dataset, or the value of another parameter
        elif data_file is not None or dataset_file is not None or from_parameter is not None:
            self.parse_column_definitions( elem )
            if data_file is not None:
                data_file = data_file.strip()
                if not os.path.isabs( data_file ):
                    full_path = os.path.join( self.tool_param.tool.app.config.tool_data_path, data_file )
                    if os.path.exists( full_path ):
                        self.index_file = data_file
                        self.file_fields = self.parse_file_fields( open( full_path ) )
                    else:
                        self.missing_index_file = data_file
            elif dataset_file is not None:
                self.dataset_ref_name = dataset_file
                self.has_dataset_dependencies = True
                self.converter_safe = False
            elif from_parameter is not None:
                transform_lines = elem.get( 'transform_lines', None )
                self.file_fields = list( load_from_parameter( from_parameter, transform_lines ) )
        
        # Load filters
        for filter_elem in elem.findall( 'filter' ):
            self.filters.append( Filter.from_element( self, filter_elem ) )
        
        # Load Validators
        for validator in elem.findall( 'validator' ):
            self.validators.append( validation.Validator.from_element( self.tool_param, validator ) )
        
        if self.dataset_ref_name:
            tool_param.data_ref = self.dataset_ref_name
            
    def parse_column_definitions( self, elem ):
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
            if not dataset: return [] #no valid dataset in history
            # Ensure parsing dynamic options does not consume more than a megabyte worth memory.
            path = dataset.file_name
            file_size = os.path.getsize( path )
            if os.path.getsize( path ) < 1048576:
                options = self.parse_file_fields( open( path ) )
            else:
                # Pass just the first megabyte to parse_file_fields. 
                import StringIO
                log.warn( "Attempting to load options from large file, reading just first megabyte" )
                contents = open( path, 'r' ).read( 1048576 )
                options = self.parse_file_fields( StringIO.StringIO( contents ) )
        elif self.tool_data_table:
            options = self.tool_data_table.get_fields()
        else:
            options = list( self.file_fields )
        for filter in self.filters:
            options = filter.filter_options( options, trans, other_values )
        return options
    
    def get_fields_by_value( self, value, trans, other_values ):
        """
        Return a list of fields with column 'value' matching provided value.
        """
        rval = []
        val_index = self.columns[ 'value' ]
        for fields in self.get_fields( trans, other_values ):
            if fields[ val_index ] == value:
                rval.append( fields )
        return rval
    
    def get_field_by_name_for_value( self, field_name, value, trans, other_values ):
        """
        Get contents of field by name for specified value.
        """
        rval = []
        if isinstance( field_name, int ):
            field_index = field_name
        else:
            assert field_name in self.columns, "Requested '%s' column missing from column def" % field_name
            field_index = self.columns[ field_name ]
        if not isinstance( value, list ):
            value = [value]
        for val in value:
            for fields in self.get_fields_by_value( val, trans, other_values ):
                rval.append( fields[ field_index ] )
        return rval
    
    def get_options( self, trans, other_values ):
        rval = []
        if self.file_fields is not None or self.tool_data_table is not None or self.dataset_ref_name is not None:
            options = self.get_fields( trans, other_values )
            for fields in options:
                rval.append( ( fields[self.columns['name']], fields[self.columns['value']], False ) )
        else:
            for filter in self.filters:
                rval = filter.filter_options( rval, trans, other_values )
        return rval
    
    def column_spec_to_index( self, column_spec ):
        """
        Convert a column specification (as read from the config file), to an
        index. A column specification can just be a number, a column name, or
        a column alias.
        """
        # Name?
        if column_spec in self.columns:
            return self.columns[column_spec]
        # Int?
        return int( column_spec )
