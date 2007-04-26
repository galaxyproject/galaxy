"""
Classes encapsulating tool parameters
"""

import logging, string, sys
from galaxy import config, datatypes, util, form_builder 
import validation
from elementtree.ElementTree import XML, Element

log = logging.getLogger(__name__)

class ToolParameter( object ):
    """
    Describes a parameter accepted by a tool. This is just a simple stub at the
    moment but in the future should encapsulate more complex parameters (lists
    of valid choices, validation logic, ...)
    """
    def __init__( self, tool, param ):
        self.tool = tool
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

    def get_html( self, trans=None, value=None, other_values={} ):
        """
        Returns the html widget corresponding to the paramter. 
        Optionally attempt to retain the current value specific by 'value'
        """
        return self.html

    def get_required_enctype( self ):
        """
        If this parameter needs the form to have a specific encoding
        return it, otherwise return None (indicating compatibility with
        any encoding)
        """
        return None
        
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
    def get_html( self, trans=None, value=None, other_values={} ):
        if self.area:
            return form_builder.TextArea( self.name, self.size, value or self.value ).get_html()
        return form_builder.TextField( self.name, self.size, value or self.value ).get_html()

class IntegerToolParameter( TextToolParameter ):
    """
    Parameter that takes an integer value.
    
    >>> p = IntegerToolParameter( None, XML( '<param name="blah" type="integer" size="4" value="10" />' ) )
    >>> print p.name
    blah
    >>> print p.get_html()
    <input type="text" name="blah" size="4" value="10">
    >>> type( p.filter_value( "10" ) )
    <type 'int'>
    >>> type( p.filter_value( "bleh" ) )
    Traceback (most recent call last):
        ...
    ValueError: An integer is required
    """
    def filter_value( self, value, trans=None, other_values={} ):
        try: return int( value )
        except: raise ValueError( "An integer is required" )
    def to_python( self, value, app ):
        return int( value )
            
class FloatToolParameter( TextToolParameter ):
    """
    Parameter that takes a real number value.
    
    >>> p = FloatToolParameter( None, XML( '<param name="blah" type="integer" size="4" value="3.141592" />' ) )
    >>> print p.name
    blah
    >>> print p.get_html()
    <input type="text" name="blah" size="4" value="3.141592">
    >>> type( p.filter_value( "36.1" ) )
    <type 'float'>
    >>> type( p.filter_value( "bleh" ) )
    Traceback (most recent call last):
        ...
    ValueError: A real number is required
    """
    def filter_value( self, value, trans=None, other_values={} ):
        try: return float( value )
        except: raise ValueError( "A real number is required")
    def to_python( self, value, app ):
        return float( value )

class BooleanToolParameter( ToolParameter ):
    """
    Parameter that takes one of two values. 
    
    >>> p = BooleanToolParameter( None, XML( '<param name="blah" type="boolean" checked="yes" truevalue="bulletproof vests" falsevalue="cellophane chests" />' ) )
    >>> print p.name
    blah
    >>> print p.get_html()
    <input type="checkbox" name="blah" value="true" checked><input type="hidden" name="blah" value="true">
    >>> print p.filter_value( ["true","true"] )
    bulletproof vests
    >>> print p.filter_value( ["true"] )
    cellophane chests
    """
    def __init__( self, tool, elem ):
        ToolParameter.__init__( self, tool, elem )
        self.truevalue = elem.get( 'truevalue', 'true' )
        self.falsevalue = elem.get( 'falsevalue', 'false' )
        self.name = elem.get( 'name' )
        self.checked = elem.get( 'checked' )
    def get_html( self, trans=None, value=None, other_values={} ):
        checked = self.checked
        if value: checked = form_builder.CheckboxField.is_checked( value )
        return form_builder.CheckboxField( self.name, checked ).get_html()
    def filter_value( self, value, trans=None, other_values={} ):
        if form_builder.CheckboxField.is_checked( value ):
            return self.truevalue
        else: 
            return self.falsevalue
    def to_python( self, value, app ):
        return ( value == 'True' )
    
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
        self.html = form_builder.FileField( elem.get( 'name') ).get_html()
    def get_required_enctype( self ):
        """
        File upload elements require the multipart/form-data encoding
        """
        return "multipart/form-data"
    def to_string( self, value, app ):
        raise Exception( "FileToolParameter cannot be persisted" )
    def to_python( self, value, app ):
        raise Exception( "FileToolParameter cannot be persisted" )
        
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
        self.dynamic_options = elem.get( "dynamic_options", None )
    def get_html( self, trans=None, value=None, other_values={} ):
        if self.dynamic_options:
            options = eval( self.dynamic_options, self.tool.code_namespace, other_values )
            self.value = options
        return form_builder.HiddenField( self.name, self.value ).get_html()
    
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
    def get_html( self, trans=None, value=None, other_values={} ):
        return form_builder.HiddenField( self.name, trans.request.base + self.value ).get_html()

class SelectToolParameter( ToolParameter ):
    """
    Parameter that takes on one (or many) or a specific set of values.
    
    TODO: There should be an alternate display that allows single selects to be 
          displayed as radio buttons and multiple selects as a set of checkboxes
    
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
    >>> print p.filter_value( ["y", "z"] )
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
    >>> print p.filter_value( ["y", "z"] )
    y,z
    """
    def __init__( self, tool, elem):
        ToolParameter.__init__( self, tool, elem )
        self.multiple = str_bool( elem.get( 'multiple', False ) )
        self.display = elem.get( 'display', None )
        self.separator = elem.get( 'separator', ',' )
        self.legal_values = set()
        self.dynamic_options = elem.get( "dynamic_options", None )
        if self.dynamic_options is None:
            self.options = list()
            for index, option in enumerate( elem.findall("option") ):
                value = option.get( "value" )
                self.legal_values.add( value )
                selected = ( option.get( "selected", None ) == "true" )
                self.options.append( ( option.text, value, selected ) )
    def get_html( self, trans=None, value=None, other_values={} ):
        if value is not None:
            if not isinstance( value, list ): value = [ value ]
        field = form_builder.SelectField( self.name, self.multiple, self.display )
        if self.dynamic_options:
            options = eval( self.dynamic_options, self.tool.code_namespace, other_values )
        else:
            options = self.options
        for text, optval, selected in options:
            if value: selected = ( optval in value )
            field.add_option( text, optval, selected )
        return field.get_html()
    def filter_value( self, value, trans=None, other_values={} ):
        if self.dynamic_options:
            legal_values = set( v for _, v, _ in eval( self.dynamic_options, self.tool.code_namespace, other_values ) )
        else:
            legal_values = self.legal_values
        if isinstance( value, list ):
            if not(self.repeat):
                assert self.multiple, "Multiple values provided but parameter is not expecting multiple values"
            rval = []
            for v in value: 
                v = util.restore_text( v )
                assert v in legal_values 
                rval.append( v )
            return self.separator.join( rval )
        else:
            value = util.restore_text( value )
            assert value in legal_values
            return value

class GenomeBuildParameter( SelectToolParameter ):
    """
    Select list that sets the last used genome build for the 
    current history as "selected".
    """
    def __init__( self, tool, elem ):
        ToolParameter.__init__( self, tool, elem )
        self.multiple = False
        self.display = elem.get( 'display', None )
        self.separator = elem.get( 'separator', ',' )
        self.legal_values = set()
        self.dynamic_options = elem.get( "dynamic_options", None )
    def get_html( self, trans=None, value=None, other_values={} ):
        if value is not None:
            if not isinstance( value, list ): 
                value = [ value ]
        field = form_builder.SelectField( self.name, False, self.display )
        last_used_build = trans.history.genome_build
        for dbkey, build_name in util.dbnames:
            if dbkey == last_used_build:
                field.add_option( build_name, dbkey, True )
            else:
                field.add_option( build_name, dbkey, False )
        return field.get_html()
    def filter_value( self, value, trans=None, other_values={} ):
        if self.dynamic_options:
            legal_values = set( v for _, v, _ in eval( self.dynamic_options, self.tool.code_namespace, other_values ) )
        else:
            legal_values = set()
            for dbkey, build_name in util.dbnames:
                legal_values.add(dbkey)
                legal_values.add(build_name)
        if isinstance( value, list ):
            if not(self.repeat):
                assert self.multiple, "Multiple values provided but parameter is not expecting multiple values"
            rval = []
            for v in value: 
                v = util.restore_text( v )
                assert v in legal_values 
                rval.append( v )
            return self.separator.join( rval )
        else:
            value = util.restore_text( value )
            assert value in legal_values
            return value

class DataToolParameter( ToolParameter ):
    """
    Parameter that takes on one (or many) or a specific set of values.

    TODO: There should be an alternate display that allows single selects to be 
          displayed as radio buttons and multiple selects as a set of checkboxes

    >>> # Mock up a history (not connected to database)
    >>> from galaxy.model import History, Dataset
    >>> from cookbook.patterns import Bunch
    >>> hist = History()
    >>> hist.flush()
    >>> hist.add_dataset( Dataset( id=1, extension='text' ) )
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
        self.format = datatypes.get_datatype_by_extension( elem.get( 'format', 'data' ).lower() )
        self.multiple = str_bool( elem.get( 'multiple', False ) )
        self.optional = str_bool( elem.get( 'optional', False ) )
        self.dynamic_options = elem.get( "dynamic_options", None )
    def get_html( self, trans=None, value=None, other_values={} ):
        assert trans is not None, "DataToolParameter requires a trans"
        history = trans.history
        assert history is not None, "DataToolParameter requires a history"
        if value is not None:
            if type( value ) != list: value = [ value ]
        field = form_builder.SelectField( self.name, self.multiple )
        some_data = False
        if self.dynamic_options:
            option_build,option_id,option_extension = eval( self.dynamic_options, self.tool.code_namespace, other_values )
        def dataset_collector( datasets, parent_hid ):            
            for i, data in enumerate( datasets ):
                if parent_hid is not None:
                    hid = "%s.%d" % ( parent_hid, i + 1 )
                else:
                    hid = str( data.hid )
                if self.dynamic_options:
                    if isinstance( data.datatype, self.format.__class__ ) and (data.dbkey == option_build) and (data.id != option_id) and (data.extension in option_extension) and not data.parent_id and not data.deleted: 
                        some_data = True
                        selected = ( value and ( data in value ) )
                        field.add_option( "%s: %s" % ( hid, data.name[:30] ), data.id, selected )
                else:
                    if isinstance( data.datatype, self.format.__class__ ) and not data.parent_id and not data.deleted:
                        some_data = True
                        selected = ( value and ( data in value ) )
                        field.add_option( "%s: %s" % ( hid, data.name[:30] ), data.id, selected )
                # Also collect children via association object
                dataset_collector( [ assoc.child for assoc in data.children ], hid )
        dataset_collector( history.datasets, None )
        if some_data and value is None:
            # Ensure that the last item is always selected
            a, b, c = field.options[-1]; field.options[-1] = a, b, True
        else:
            # HACK: we should just disable the form or something
            field.add_option( "no data has the proper type", '' )                
        if self.optional == True:
            field.add_option( "Selection is Optional", 'None', True )
        return field.get_html()
    def filter_value( self, value, trans, other_values={} ):
        if not value:
            raise ValueError( "A data of the appropriate type is required" )
        if value in [None, "None"]:
            temp_data = trans.app.model.Dataset()
            temp_data.state = temp_data.states.FAKE
            return temp_data
        if isinstance( value, list ):
            return [ trans.app.model.Dataset.get( v ) for v in value ]
        else:
            return trans.app.model.Dataset.get( value )
    def to_string( self, value, app ):
        return value.id
    def to_python( self, value, app ):
        return app.model.Dataset.get( int( value ) )

class RawToolParameter( ToolParameter ):
    """
    Completely nondescript parameter, HTML representation is provided as text
    contents. 
    
    >>> p = RawToolParameter( None, XML( 
    ... '''
    ... <param name="blah" type="raw">
    ... <![CDATA[<span id="$name">Some random stuff</span>]]>
    ... </param>
    ... ''' ) )
    >>> print p.name
    blah
    >>> print p.get_html().strip()
    <span id="blah">Some random stuff</span>
    """
    def __init__( self, tool, elem ):
        ToolParameter.__init__( self, tool, elem )
        template = string.Template( elem.text )
        self.html = template.substitute( self.__dict__ )
        
# class HistoryIDParameter( ToolParameter ):
#     """
#     Parameter that takes a name value, makes history.id available. 
#     
#     FIXME: This is a hack (esp. if hidden params are a hack) but in order to
#            have the history accessable at the job level, it is necessary
#            I also probably wrote this docstring test thing wrong.
#     
#     >>> from galaxy.model import History, Dataset
#     >>> from cookbook.patterns import Bunch
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
                        hidden      = HiddenToolParameter,
                        baseurl     = BaseURLToolParameter,
                        file        = FileToolParameter,
                        data        = DataToolParameter,
                        raw         = RawToolParameter )

def get_suite():
    """Get unittest suite for this module"""
    import doctest, sys
    return doctest.DocTestSuite( sys.modules[__name__] )

def str_bool(in_str):
    """
    returns true/false of a string, since bool(str), always returns true if string is not empty
    default action is to return false
    """
    if str(in_str).lower() == 'true':
        return True
    return False
