"""
Classes encapsulating tool parameters
"""

import logging, string, sys
from galaxy import config, datatypes, util
from galaxy.datatypes.tabular import *
import validation, dynamic_options
from elementtree.ElementTree import XML, Element

# For BaseURLToolParameter
from galaxy.web import url_for
from galaxy.web import form_builder
from galaxy.model import Dataset

log = logging.getLogger(__name__)

class ToolParameter( object ):
    """
    Describes a parameter accepted by a tool. This is just a simple stub at the
    moment but in the future should encapsulate more complex parameters (lists
    of valid choices, validation logic, ...)
    """
    def __init__( self, tool, param, context=None ):
        self.tool = tool
        self.refresh_on_change = False
        self.name = param.get("name")
        self.type = param.get("type")
        self.label = util.xml_text(param, "label")
        self.help = util.xml_text(param, "help")
        self.html = "no html set"
        self.repeat = param.get("repeat", None)
        self.condition = param.get( "condition", None )
        self.validators = []
        for elem in param.findall("validator"):
            self.validators.append( validation.Validator.from_element( elem ) )

    def get_label( self ):
        """Return user friendly name for the parameter"""
        if self.label: return self.label
        else: return self.name

    def get_html_field( self, trans=None, value=None, other_values={} ):
        raise TypeError( "Abstract Method" )

    def get_html( self, trans=None, value=None, other_values={}):
        """
        Returns the html widget corresponding to the paramter. 
        Optionally attempt to retain the current value specific by 'value'
        """
        return self.get_html_field( trans, value, other_values ).get_html()
        
    def from_html( self, value, trans=None, other_values={} ):
        """
        Convert a value from an HTML POST into the parameters prefered value 
        format. 
        """
        return value
        
    def get_initial_value( self, trans, context ):
        """
        Return the starting value of the parameter
        """
        return None

    def get_required_enctype( self ):
        """
        If this parameter needs the form to have a specific encoding
        return it, otherwise return None (indicating compatibility with
        any encoding)
        """
        return None
        
    def get_dependencies( self ):
        """
        Return the names of any other parameters this parameter depends on
        """
        return []
        
    def filter_value( self, value, trans=None, other_values={} ):
        """
        Parse the value returned by the view into a form usable by the tool OR
        raise a ValueError.
        """
        return value
        
    def to_string( self, value, app ):
        """Convert a value to a string representation suitable for persisting"""
        return str( value )
    
    def to_python( self, value, app ):
        """Convert a value created with to_string back to an object representation"""
        return value
        
    def value_to_basic( self, value, app ):
        return self.to_string( value, app )
        
    def value_from_basic( self, value, app, ignore_errors=False ):
        # HACK: Some things don't deal with unicode well, psycopg problem?
        if type( value ) == unicode:
            value = str( value )
        if ignore_errors:
            try:
                return self.to_python( value, app )
            except:
                return value
        else:
            return self.to_python( value, app )
            
    def value_to_display_text( self, value, app ):
        """
        Convert a value to a text representation suitable for displaying to
        the user
        """
        return value
        
    def to_param_dict_string( self, value ):
        return str( value )
        
    def validate( self, value, history=None ):
        for validator in self.validators:
            validator.validate( value, history )

    @classmethod
    def build( cls, tool, param ):
        """Factory method to create parameter of correct type"""
        param_type = param.get("type")
        if not param_type or param_type not in parameter_types:
            raise ValueError( "Unknown tool parameter type '%s'" % param_type )
        else:
            return parameter_types[param_type]( tool, param )
        
class TextToolParameter( ToolParameter ):
    """
    Parameter that can take on any text value.
    
    >>> p = TextToolParameter( None, XML( '<param name="blah" type="text" size="4" value="default" />' ) )
    >>> print p.name
    blah
    >>> print p.get_html()
    <input type="text" name="blah" size="4" value="default">
    >>> print p.get_html( value="meh" )
    <input type="text" name="blah" size="4" value="meh">
    """
    def __init__( self, tool, elem ):
        ToolParameter.__init__( self, tool, elem )
        self.name = elem.get( 'name' )
        self.size = elem.get( 'size' )
        self.value = elem.get( 'value' )
        self.area = str_bool( elem.get( 'area', False ) )
    def get_html_field( self, trans=None, value=None, other_values={} ):
        if self.area:
            return form_builder.TextArea( self.name, self.size, value or self.value )
        else:
            return form_builder.TextField( self.name, self.size, value or self.value )
    def get_initial_value( self, trans, context ):
        return self.value

class IntegerToolParameter( TextToolParameter ):
    """
    Parameter that takes an integer value.
    
    >>> p = IntegerToolParameter( None, XML( '<param name="blah" type="integer" size="4" value="10" />' ) )
    >>> print p.name
    blah
    >>> print p.get_html()
    <input type="text" name="blah" size="4" value="10">
    >>> type( p.from_html( "10" ) )
    <type 'int'>
    >>> type( p.from_html( "bleh" ) )
    Traceback (most recent call last):
        ...
    ValueError: An integer is required
    """
    def from_html( self, value, trans=None, other_values={} ):
        try: return int( value )
        except: raise ValueError( "An integer is required" )
    def to_python( self, value, app ):
        return int( value )
    def get_initial_value( self, trans, context ):
        return int( self.value )
            
class FloatToolParameter( TextToolParameter ):
    """
    Parameter that takes a real number value.
    
    >>> p = FloatToolParameter( None, XML( '<param name="blah" type="integer" size="4" value="3.141592" />' ) )
    >>> print p.name
    blah
    >>> print p.get_html()
    <input type="text" name="blah" size="4" value="3.141592">
    >>> type( p.from_html( "36.1" ) )
    <type 'float'>
    >>> type( p.from_html( "bleh" ) )
    Traceback (most recent call last):
        ...
    ValueError: A real number is required
    """
    def from_html( self, value, trans=None, other_values={} ):
        try: return float( value )
        except: raise ValueError( "A real number is required" )
    def to_python( self, value, app ):
        return float( value )
    def get_initial_value( self, trans, context ):
        return float( self.value )

class BooleanToolParameter( ToolParameter ):
    """
    Parameter that takes one of two values. 
    
    >>> p = BooleanToolParameter( None, XML( '<param name="blah" type="boolean" checked="yes" truevalue="bulletproof vests" falsevalue="cellophane chests" />' ) )
    >>> print p.name
    blah
    >>> print p.get_html()
    <input type="checkbox" name="blah" value="true" checked><input type="hidden" name="blah" value="true">
    >>> print p.from_html( ["true","true"] )
    True
    >>> print p.to_param_dict_string( True )
    bulletproof vests
    >>> print p.from_html( ["true"] )
    False
    >>> print p.to_param_dict_string( False )
    cellophane chests
    """
    def __init__( self, tool, elem ):
        ToolParameter.__init__( self, tool, elem )
        self.truevalue = elem.get( 'truevalue', 'true' )
        self.falsevalue = elem.get( 'falsevalue', 'false' )
        self.name = elem.get( 'name' )
        self.checked = str_bool( elem.get( 'checked' ) )
    def get_html_field( self, trans=None, value=None, other_values={} ):
        checked = self.checked
        if value: 
            checked = form_builder.CheckboxField.is_checked( value )
        return form_builder.CheckboxField( self.name, checked )
    def from_html( self, value, trans=None, other_values={} ):
        return form_builder.CheckboxField.is_checked( value )  
    def to_python( self, value, app ):
        return ( value == 'True' )
    def get_initial_value( self, trans, context ):
        return self.checked
    def to_param_dict_string( self, value ):
        if value:
            return self.truevalue
        else:
            return self.falsevalue

class FileToolParameter( ToolParameter ):
    """
    Parameter that takes an uploaded file as a value.
    
    >>> p = FileToolParameter( None, XML( '<param name="blah" type="file"/>' ) )
    >>> print p.name
    blah
    >>> print p.get_html()
    <input type="file" name="blah">
    """
    def __init__( self, tool, elem ):
        """
        Example: C{<param name="bins" type="file" />}
        """
        ToolParameter.__init__( self, tool, elem )
        self.name = elem.get( 'name' )
    def get_html_field( self, trans=None, value=None, other_values={}  ):
        return form_builder.FileField( self.name )
    def get_required_enctype( self ):
        """
        File upload elements require the multipart/form-data encoding
        """
        return "multipart/form-data"
    def to_string( self, value, app ):
        if value is None:
            return None
        else:
            raise Exception( "FileToolParameter cannot be persisted" )
    def to_python( self, value, app ):
        if value is None:
            return None
        else:
            raise Exception( "FileToolParameter cannot be persisted" )
    def get_initial_value( self, trans, context ):
        return None
        
class HiddenToolParameter( ToolParameter ):
    """
    Parameter that takes one of two values. 
    
    FIXME: This seems hacky, parameters should only describe things the user
           might change. It is used for 'initializing' the UCSC proxy tool
    
    >>> p = HiddenToolParameter( None, XML( '<param name="blah" type="hidden" value="wax so rockin"/>' ) )
    >>> print p.name
    blah
    >>> print p.get_html()
    <input type="hidden" name="blah" value="wax so rockin">
    """    
    def __init__( self, tool, elem ):
        ToolParameter.__init__( self, tool, elem )
        self.name = elem.get( 'name' )
        self.value = elem.get( 'value' )
    def get_html_field( self, trans=None, value=None, other_values={} ):
        return form_builder.HiddenField( self.name, self.value )
    def get_initial_value( self, trans, context ):
        return self.value
    
## This is clearly a HACK, parameters should only be used for things the user
## can change, there needs to be a different way to specify this. I'm leaving
## it for now to avoid breaking any tools.

class BaseURLToolParameter( ToolParameter ):
    """
    Returns a parameter the contains its value prepended by the 
    current server base url. Used in all redirects.
    """
    def __init__( self, tool, elem ):
        ToolParameter.__init__( self, tool, elem )
        self.name = elem.get( 'name' )
        self.value = elem.get( 'value', '' )
    def get_value( self, trans ):
        # url = trans.request.base + self.value
        url = url_for( self.value, qualified=True )
        return url
    def get_html_field( self, trans=None, value=None, other_values={} ):
        return form_builder.HiddenField( self.name, self.get_value( trans ) )
    def get_initial_value( self, trans, context ):
        return self.value

class SelectToolParameter( ToolParameter ):
    """
    Parameter that takes on one (or many) or a specific set of values.
    
    >>> p = SelectToolParameter( None, XML( 
    ... '''
    ... <param name="blah" type="select">
    ...     <option value="x">I am X</option>
    ...     <option value="y" selected="true">I am Y</option>
    ...     <option value="z">I am Z</option>
    ... </param>
    ... ''' ) )
    >>> print p.name
    blah
    >>> print p.get_html()
    <select name="blah">
    <option value="x">I am X</option>
    <option value="y" selected>I am Y</option>
    <option value="z">I am Z</option>
    </select>
    >>> print p.get_html( value="z" )
    <select name="blah">
    <option value="x">I am X</option>
    <option value="y">I am Y</option>
    <option value="z" selected>I am Z</option>
    </select>
    >>> print p.filter_value( "y" )
    y

    >>> p = SelectToolParameter( None, XML( 
    ... '''
    ... <param name="blah" type="select" multiple="true">
    ...     <option value="x">I am X</option>
    ...     <option value="y" selected="true">I am Y</option>
    ...     <option value="z" selected="true">I am Z</option>
    ... </param>
    ... ''' ) )
    >>> print p.name
    blah
    >>> print p.get_html()
    <select name="blah" multiple>
    <option value="x">I am X</option>
    <option value="y" selected>I am Y</option>
    <option value="z" selected>I am Z</option>
    </select>
    >>> print p.get_html( value=["x","y"])
    <select name="blah" multiple>
    <option value="x" selected>I am X</option>
    <option value="y" selected>I am Y</option>
    <option value="z">I am Z</option>
    </select>
    >>> print p.to_param_dict_string( ["y", "z"] )
    y,z
    
    >>> p = SelectToolParameter( None, XML( 
    ... '''
    ... <param name="blah" type="select" multiple="true" display="checkboxes">
    ...     <option value="x">I am X</option>
    ...     <option value="y" selected="true">I am Y</option>
    ...     <option value="z" selected="true">I am Z</option>
    ... </param>
    ... ''' ) )
    >>> print p.name
    blah
    >>> print p.get_html()
    <div><input type="checkbox" name="blah" value="x">I am X</div>
    <div class="odd_row"><input type="checkbox" name="blah" value="y" checked>I am Y</div>
    <div><input type="checkbox" name="blah" value="z" checked>I am Z</div>
    >>> print p.get_html( value=["x","y"])
    <div><input type="checkbox" name="blah" value="x" checked>I am X</div>
    <div class="odd_row"><input type="checkbox" name="blah" value="y" checked>I am Y</div>
    <div><input type="checkbox" name="blah" value="z">I am Z</div>
    >>> print p.to_param_dict_string( ["y", "z"] )
    y,z
    """
    def __init__( self, tool, elem):
        ToolParameter.__init__( self, tool, elem )
        self.multiple = str_bool( elem.get( 'multiple', False ) )
        self.display = elem.get( 'display', None )
        self.separator = elem.get( 'separator', ',' )
        self.legal_values = set()
        self.dynamic_options = elem.get( "dynamic_options", None )
        options = elem.find( 'options' )
        if options is None:
            self.options = None
        else:
            self.options = dynamic_options.DynamicOptions( options )
        if self.dynamic_options is None and self.options is None:
            self.static_options = list()
            for index, option in enumerate( elem.findall( "option" ) ):
                value = option.get( "value" )
                self.legal_values.add( value )
                selected = ( option.get( "selected", None ) == "true" )
                self.static_options.append( ( option.text, value, selected ) )
        self.is_dynamic = ( ( self.dynamic_options is not None ) or ( self.options is not None ) ) 
    def get_options( self, trans, other_values ):
        if self.options:
            return self.options.get_options( trans, other_values )
        elif self.dynamic_options:
            return eval( self.dynamic_options, self.tool.code_namespace, other_values )
        else:
            return self.static_options
    def get_legal_values( self, trans, other_values ):
        if self.options:
            return set( v for _, v, _ in self.options.get_options( trans, other_values, must_be_valid = True ) )
        elif self.dynamic_options:
            return set( v for _, v, _ in eval( self.dynamic_options, self.tool.code_namespace, other_values ) )
        else:
            return self.legal_values
    def get_html_field( self, trans=None, value=None, other_values={} ):
        # Dynamic options are not yet supported in workflow, allow 
        # specifying the value as text for now.
        if self.is_dynamic and trans.workflow_building_mode:
            if self.multiple:
                if value is None:
                    value = ""
                else:
                    value = "\n".join( value )
                return form_builder.TextArea( self.name, value=value )
            else:
                return form_builder.TextField( self.name, value=(value or "") )
        if value is not None:
            if not isinstance( value, list ): value = [ value ]
        field = form_builder.SelectField( self.name, self.multiple, self.display, self.refresh_on_change )
        options = self.get_options( trans, other_values )
        for text, optval, selected in options:
            if value: 
                selected = ( optval in value )
            field.add_option( text, optval, selected )
        return field
    def from_html( self, value, trans=None, other_values={} ):
        if self.is_dynamic and trans.workflow_building_mode:
            return value
        legal_values = self.get_legal_values( trans, other_values )
        if isinstance( value, list ):
            if not(self.repeat):
                assert self.multiple, "Multiple values provided but parameter is not expecting multiple values"
            rval = []
            for v in value: 
                v = util.restore_text( v )
                if v not in legal_values:
                    raise ValueError( "An invalid option was selected, please verify" )
                rval.append( v )
            return rval
        else:
            value = util.restore_text( value )
            if value not in legal_values:
                raise ValueError( "An invalid option was selected, please verify" )
            return value    
    def to_param_dict_string( self, value ):
        if value is None:
            return "None"
        if isinstance( value, list ):
            if not(self.repeat):
                assert self.multiple, "Multiple values provided but parameter is not expecting multiple values"
            return self.separator.join( value )
        else:
            return value
    def value_to_basic( self, value, app ):
        return value
    def get_initial_value( self, trans, context ):
        # More working around dynamic options for workflow
        if self.is_dynamic and trans.workflow_building_mode:
            # Really the best we can do?
            return None
        options = list( self.get_options( trans, context ) )
        value = [ optval for _, optval, selected in options if selected ]
        if len( value ) == 0:
            if not self.multiple and options:
                # Nothing selected, but not a multiple select, with some values,
                # so we have to default to something (the HTML form will anyway)
                # TODO: deal with optional parameters in a better way
                value = options[0][1]
            else:
                value = None
        elif len( value ) == 1:
            value = value[0]
        return value
    def get_dependencies( self ):
        data_ref = param_ref = None
        if self.options:
            try: data_ref = self.options.data_ref
            except: pass
            try: param_ref = self.options.param_ref
            except: pass
        if data_ref is None and param_ref is None: return []
        elif data_ref is None: return [ param_ref ]
        elif param_ref is None: return [ data_ref ]
        else: return [ data_ref, param_ref ]

class GenomeBuildParameter( SelectToolParameter ):
    """
    Select list that sets the last used genome build for the current history 
    as "selected".
    
    >>> # Create a mock transcation with 'hg17' as the current build
    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch( history=Bunch( genome_build='hg17' ) )
    
    >>> p = GenomeBuildParameter( None, XML( 
    ... '''
    ... <param name="blah" type="genomebuild" />
    ... ''' ) )
    >>> print p.name
    blah
    
    >>> # hg17 should be selected by default
    >>> print p.get_html( trans ) # doctest: +ELLIPSIS
    <select name="blah">
    <option value="?">unspecified (?)</option>
    ...
    <option value="hg18">Human Mar. 2006 (hg18)</option>
    <option value="hg17" selected>Human May 2004 (hg17)</option>
    ...
    </select>
    
    >>> # If the user selected something else already, that should be used
    >>> # instead
    >>> print p.get_html( trans, value='hg18' ) # doctest: +ELLIPSIS
    <select name="blah">
    <option value="?">unspecified (?)</option>
    ...
    <option value="hg18" selected>Human Mar. 2006 (hg18)</option>
    <option value="hg17">Human May 2004 (hg17)</option>
    ...
    </select>
    
    >>> print p.filter_value( "hg17" )
    hg17
    """
    def get_options( self, trans, other_values ):
        last_used_build = trans.history.genome_build
        for dbkey, build_name in util.dbnames:
            yield build_name, dbkey, ( dbkey == last_used_build )
    def get_legal_values( self, trans, other_values ):
        return set( dbkey for dbkey, _ in util.dbnames )

class ColumnListParameter( SelectToolParameter ):
    """
    Select list that consists of either the total number of columns or only
    those columns that contain numerical values in the associated DataToolParameter.
    
    # TODO: we need better testing here, but not sure how to associate a DatatoolParameter with a ColumnListParameter
    # from a twill perspective...

    >>> # Mock up a history (not connected to database)
    >>> from galaxy.model import History, Dataset
    >>> from galaxy.util.bunch import Bunch
    >>> hist = History()
    >>> hist.flush()
    >>> hist.add_dataset( Dataset( id=1, extension='interval' ) )
    >>> dtp =  DataToolParameter( None, XML( '<param name="blah" type="data" format="interval"/>' ) )
    >>> print dtp.name
    blah
    >>> clp = ColumnListParameter ( None, XML( '<param name="numerical_column" type="data_column" data_ref="blah" numerical="true"/>' ) )
    >>> print clp.name
    numerical_column
    """
    def __init__( self, tool, elem ):
        SelectToolParameter.__init__( self, tool, elem )
        self.tool = tool
        self.numerical = str_bool( elem.get( "numerical", False ))
        self.force_select = str_bool( elem.get( "force_select", True ))
        self.accept_default = str_bool( elem.get( "accept_default", False ))
        self.data_ref = elem.get( "data_ref", None )
        self.is_dynamic = True
    def get_column_list( self, trans, other_values ):
        """
        Generate a select list containing the columns of the associated 
        dataset (if found).
        """
        column_list = []
        # No value indicates a configuration error, the named DataToolParameter
        # must preceed this parameter in the config
        assert self.data_ref in other_values, "Value for associated DataToolParameter not found"
        # Get the value of the associated DataToolParameter (a dataset)
        dataset = other_values[ self.data_ref ]
        # Check if a dataset is selected
        if dataset is None or dataset == '':
            # NOTE: Both of these values indicate that no dataset is selected.
            #       However, 'None' indicates that the dataset is optional 
            #       while '' indicates that it is not. Currently column
            #       parameters do not work well with optional datasets
            return column_list
        # Generate options
        if not dataset.metadata.columns:
            if self.accept_default:
                column_list.append( '1' )
            return column_list
        if not self.force_select:
            column_list.append( 'None' )
        if self.numerical:
            # If numerical was requsted, filter columns based on metadata
            for i, col in enumerate( dataset.metadata.column_types ):
                if col == 'int' or col == 'float':
                    column_list.append( str( i + 1 ) )
        else:
            for i in range(0, dataset.metadata.columns):
                column_list.append( str( i + 1 ) )
        return column_list
    def get_options( self, trans, other_values ):
        options = []
        column_list = self.get_column_list( trans, other_values )
        if len( column_list ) > 0 and not self.force_select:
            options.append( ('?', 'None', False) )
        for col in column_list:
            if col != 'None':
                options.append( ( 'c' + col, col, False ) )
        return options
    def get_legal_values( self, trans, other_values ):
        return set( self.get_column_list( trans, other_values ) )
    def get_dependencies( self ):
        return [ self.data_ref ]

class DataToolParameter( ToolParameter ):
    """
    Parameter that takes on one (or many) or a specific set of values.

    TODO: There should be an alternate display that allows single selects to be 
          displayed as radio buttons and multiple selects as a set of checkboxes

    >>> # Mock up a history (not connected to database)
    >>> from galaxy.model import History, Dataset
    >>> from galaxy.util.bunch import Bunch
    >>> hist = History()
    >>> hist.flush()
    >>> hist.add_dataset( Dataset( id=1, extension='txt' ) )
    >>> hist.add_dataset( Dataset( id=2, extension='bed' ) )
    >>> hist.add_dataset( Dataset( id=3, extension='fasta' ) )
    >>> hist.add_dataset( Dataset( id=4, extension='png' ) )
    >>> hist.add_dataset( Dataset( id=5, extension='interval' ) )
    >>> p = DataToolParameter( None, XML( '<param name="blah" type="data" format="interval"/>' ) )
    >>> print p.name
    blah
    >>> print p.get_html( trans=Bunch( history=hist ) )
    <select name="blah">
    <option value="2">2: Unnamed dataset</option>
    <option value="5" selected>5: Unnamed dataset</option>
    </select>
    """

    def __init__( self, tool, elem ):
        ToolParameter.__init__( self, tool, elem )
        # Add metadata validator
        self.validators.append( validation.MetadataValidator() )
        # Build tuple of classes for supported data formats
        formats = []
        self.extensions = elem.get( 'format', 'data' ).split( "," )
        for extension in self.extensions:
            extension = extension.strip()
            if tool is None:
                #This occurs for things such as unit tests
                import galaxy.datatypes.registry
                formats.append( galaxy.datatypes.registry.Registry().get_datatype_by_extension( extension.lower() ).__class__ )
            else:
                formats.append( tool.app.datatypes_registry.get_datatype_by_extension( extension.lower() ).__class__ )
        self.formats = tuple( formats )
        self.multiple = str_bool( elem.get( 'multiple', False ) )
        self.optional = str_bool( elem.get( 'optional', False ) )

    def get_html_field( self, trans=None, value=None, other_values={} ):
        assert trans is not None, "DataToolParameter requires a trans"
        history = trans.history
        assert history is not None, "DataToolParameter requires a history"
        if value is not None:
            if type( value ) != list: value = [ value ]
        field = form_builder.SelectField( self.name, self.multiple, None, self.refresh_on_change )
        # CRUCIAL: the dataset_collector function needs to be local to DataToolParameter.get_html_field()
        def dataset_collector( datasets, parent_hid ):
            for i, data in enumerate( datasets ):
                if parent_hid is not None:
                    hid = "%s.%d" % ( parent_hid, i + 1 )
                else:
                    hid = str( data.hid )
                if isinstance( data.datatype, self.formats) and not data.deleted and data.state not in [data.states.ERROR]:
                    selected = ( value and ( data in value ) )
                    field.add_option( "%s: %s" % ( hid, data.name[:30] ), data.id, selected )
                # Also collect children via association object
                dataset_collector( [ assoc.child for assoc in data.children ], hid )
        dataset_collector( history.datasets, None )
        some_data = bool( field.options )
        if some_data:
            if value is None:
                # Ensure that the last item is always selected
                a, b, c = field.options[-1]; field.options[-1] = a, b, True
        else:
            # HACK: we should just disable the form or something
            field.add_option( "no data has the proper type", '' )                
        if self.optional == True:
            field.add_option( "Selection is Optional", 'None', True )
        return field

    def get_initial_value( self, trans, context ):
        """
        NOTE: This is wasteful since dynamic options and dataset collection
              happens twice (here and when generating HTML). 
        """
        # Can't look at history in workflow mode
        if trans.workflow_building_mode:
            return None
        assert trans is not None, "DataToolParameter requires a trans"
        history = trans.history
        assert history is not None, "DataToolParameter requires a history"
        history = trans.history
        most_recent_dataset = [None]
        def dataset_collector( datasets ):
            for i, data in enumerate( datasets ):
                if isinstance( data.datatype, self.formats) and not data.deleted and data.state not in [data.states.ERROR]:
                    most_recent_dataset[0] = data
                # Also collect children via association object
                dataset_collector( [ assoc.child for assoc in data.children ] )
        dataset_collector( history.datasets )
        most_recent_dataset = most_recent_dataset.pop()
        if most_recent_dataset is not None:
            return most_recent_dataset
        elif self.optional:
            return None
        else:
            return ''

    def from_html( self, value, trans, other_values={} ):
        # Can't look at history in workflow mode, skip validation and such
        if trans.workflow_building_mode:
            return None
        if not value:
            raise ValueError( "A data of the appropriate type is required" ) 
        if value in [None, "None"]:
            temp_data = trans.app.model.Dataset( extension = 'data' )
            temp_data.state = temp_data.states.OK
            return temp_data
        if isinstance( value, list ):
            return [ trans.app.model.Dataset.get( v ) for v in value ]
        else:
            return trans.app.model.Dataset.get( value )

    def value_to_basic( self, value, app ):
        if value is None:
            return None
        if isinstance( value, str ):
            return value
        return value.id

    def value_from_basic( self, value, app, ignore_errors=False ):
        """
        Both of these values indicate that no dataset is selected.  However, 'None' 
        indicates that the dataset is optional, while '' indicates that it is not.
        """
        if value is None or value =='':
            return value
        try:
            return app.model.Dataset.get( int( value ) )
        except:
            if ignore_errors:
                return value
            else:
                raise

    def to_param_dict_string( self, value ):
        return value.file_name
        
    def value_to_display_text( self, value, app ):
        return "%s: %s" % ( value.hid, value.name )

# class RawToolParameter( ToolParameter ):
#     """
#     Completely nondescript parameter, HTML representation is provided as text
#     contents. 
#     
#     >>> p = RawToolParameter( None, XML( 
#     ... '''
#     ... <param name="blah" type="raw">
#     ... <![CDATA[<span id="$name">Some random stuff</span>]]>
#     ... </param>
#     ... ''' ) )
#     >>> print p.name
#     blah
#     >>> print p.get_html().strip()
#     <span id="blah">Some random stuff</span>
#     """
#     def __init__( self, tool, elem ):
#         ToolParameter.__init__( self, tool, elem )
#         self.template = string.Template( elem.text )
#     def get_html( self, prefix="" ):
#         context = dict( self.__dict__ )
#         context.update( dict( prefix=prefix ) )
#         return self.template.substitute( context )
        
# class HistoryIDParameter( ToolParameter ):
#     """
#     Parameter that takes a name value, makes history.id available. 
#     
#     FIXME: This is a hack (esp. if hidden params are a hack) but in order to
#            have the history accessable at the job level, it is necessary
#            I also probably wrote this docstring test thing wrong.
#     
#     >>> from galaxy.model import History, Dataset
#     >>> from galaxy.util.bunch import Bunch
#     >>> hist = History( id=1 )
#     >>> p = HistoryIDParameter( None, XML( '<param name="blah" type="history"/>' ) )
#     >>> print p.name
#     blah
#     >>> html_string = '<input type="hidden" name="blah" value="%d">' % hist.id
#     >>> assert p.get_html( trans=Bunch( history=hist ) ) == html_string
#     """  
#     def __init__( self, tool, elem ):
#         ToolParameter.__init__( self, tool, elem )
#         self.name = elem.get('name')
#     def get_html( self, trans, value=None, other_values={} ):
#         assert trans.history is not None, "HistoryIDParameter requires a history"
#         self.html = form_builder.HiddenField( self.name, trans.history.id ).get_html()
#         return self.html

parameter_types = dict( text        = TextToolParameter,
                        integer     = IntegerToolParameter,
                        float       = FloatToolParameter,
                        boolean     = BooleanToolParameter,
                        genomebuild = GenomeBuildParameter,
                        select      = SelectToolParameter,
                        data_column = ColumnListParameter,
                        hidden      = HiddenToolParameter,
                        baseurl     = BaseURLToolParameter,
                        file        = FileToolParameter,
                        data        = DataToolParameter )


def str_bool(in_str):
    """
    returns true/false of a string, since bool(str), always returns true if string is not empty
    default action is to return false
    """
    if str(in_str).lower() == 'true' or str(in_str).lower() == 'yes':
        return True
    return False
