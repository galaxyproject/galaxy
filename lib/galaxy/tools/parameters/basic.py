"""
Basic tool parameters.
"""
import logging
import os
import os.path
import re
from xml.etree.ElementTree import XML

from six import string_types

import galaxy.model
import galaxy.tools.parser
from galaxy import util
from galaxy.util import (
    sanitize_param,
    string_as_bool,
    unicodify
)
from galaxy.util.bunch import Bunch
from galaxy.util.dictifiable import Dictifiable
from galaxy.util.expressions import ExpressionContext
from galaxy.web import url_for

from . import validation
from .dataset_matcher import (
    DatasetCollectionMatcher,
    DatasetMatcher
)
from .sanitize import ToolParameterSanitizer
from ..parameters import (
    dynamic_options,
    history_query
)
from ..parser import get_input_source as ensure_input_source

log = logging.getLogger( __name__ )

workflow_building_modes = Bunch( DISABLED=False, ENABLED=True, USE_HISTORY=1 )

WORKFLOW_PARAMETER_REGULAR_EXPRESSION = re.compile( '''\$\{.+?\}''' )


def contains_workflow_parameter( value, search=False ):
    if not isinstance( value, string_types ):
        return False
    if search and WORKFLOW_PARAMETER_REGULAR_EXPRESSION.search( value ):
        return True
    if not search and WORKFLOW_PARAMETER_REGULAR_EXPRESSION.match( value ):
        return True
    return False


def parse_dynamic_options( param, input_source ):
    options_elem = input_source.parse_dynamic_options_elem()
    if options_elem is not None:
        return dynamic_options.DynamicOptions( options_elem, param )
    return None


class ToolParameter( object, Dictifiable ):
    """
    Describes a parameter accepted by a tool. This is just a simple stub at the
    moment but in the future should encapsulate more complex parameters (lists
    of valid choices, validation logic, ...)
    """
    dict_collection_visible_keys = ( 'name', 'argument', 'type', 'label', 'help', 'refresh_on_change' )

    def __init__( self, tool, input_source, context=None ):
        input_source = ensure_input_source(input_source)
        self.tool = tool
        self.refresh_on_change_values = []
        self.argument = input_source.get( "argument" )
        self.name = ToolParameter.parse_name( input_source )
        self.type = input_source.get( "type" )
        self.hidden = input_source.get( "hidden", False )
        self.refresh_on_change = input_source.get_bool( "refresh_on_change", False )
        self.optional = input_source.parse_optional()
        self.is_dynamic = False
        self.label = input_source.parse_label()
        self.help = input_source.parse_help()
        sanitizer_elem = input_source.parse_sanitizer_elem()
        if sanitizer_elem is not None:
            self.sanitizer = ToolParameterSanitizer.from_element( sanitizer_elem )
        else:
            self.sanitizer = None
        self.validators = []
        for elem in input_source.parse_validator_elems():
            self.validators.append( validation.Validator.from_element( self, elem ) )

    @property
    def visible( self ):
        """Return true if the parameter should be rendered on the form"""
        return True

    def get_label( self ):
        """Return user friendly name for the parameter"""
        return self.label if self.label else self.name

    def from_json( self, value, trans=None, other_values={} ):
        """
        Convert a value from an HTML POST into the parameters preferred value
        format.
        """
        return value

    def get_initial_value( self, trans, other_values ):
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

    def to_json( self, value, app, use_security ):
        """Convert a value to a string representation suitable for persisting"""
        return unicodify( value )

    def to_python( self, value, app ):
        """Convert a value created with to_json back to an object representation"""
        return value

    def value_to_basic( self, value, app, use_security=False ):
        if isinstance( value, RuntimeValue ):
            return { '__class__': 'RuntimeValue' }
        elif isinstance( value, dict ):
            if value.get( '__class__' ) == 'RuntimeValue':
                return value
        return self.to_json( value, app, use_security )

    def value_from_basic( self, value, app, ignore_errors=False ):
        # Handle Runtime and Unvalidated values
        if isinstance( value, dict ) and value.get( '__class__' ) == 'RuntimeValue':
            return RuntimeValue()
        elif isinstance( value, dict ) and value.get( '__class__' ) == 'UnvalidatedValue':
            return value[ 'value' ]
        # Delegate to the 'to_python' method
        if ignore_errors:
            try:
                return self.to_python( value, app )
            except:
                return value
        else:
            return self.to_python( value, app )

    def value_to_display_text( self, value, app=None ):
        """
        Convert a value to a text representation suitable for displaying to
        the user
        >>> p = ToolParameter( None, XML( '<param name="_name" />' ) )
        >>> print p.value_to_display_text( None )
        Not available.
        >>> print p.value_to_display_text( '' )
        Empty.
        >>> print p.value_to_display_text( 'text' )
        text
        >>> print p.value_to_display_text( True )
        True
        >>> print p.value_to_display_text( False )
        False
        >>> print p.value_to_display_text( 0 )
        0
        """
        if value is not None:
            str_value = unicodify( value )
            if not str_value:
                return "Empty."
            return str_value
        return "Not available."

    def to_param_dict_string( self, value, other_values={} ):
        """Called via __str__ when used in the Cheetah template"""
        if value is None:
            value = ""
        elif not isinstance( value, string_types ):
            value = str( value )
        if self.tool is None or self.tool.options.sanitize:
            if self.sanitizer:
                value = self.sanitizer.sanitize_param( value )
            else:
                value = sanitize_param( value )
        return value

    def validate( self, value, trans=None ):
        if value in [ "", None ] and self.optional:
            return
        for validator in self.validators:
            validator.validate( value, trans )

    def to_dict( self, trans, other_values={} ):
        """ to_dict tool parameter. This can be overridden by subclasses. """
        tool_dict = super( ToolParameter, self ).to_dict()
        tool_dict[ 'model_class' ] = self.__class__.__name__
        tool_dict[ 'optional' ] = self.optional
        tool_dict[ 'hidden' ] = self.hidden
        tool_dict[ 'is_dynamic' ] = self.is_dynamic
        if hasattr( self, 'value' ):
            tool_dict[ 'value' ] = self.value
        return tool_dict

    @classmethod
    def build( cls, tool, param ):
        """Factory method to create parameter of correct type"""
        param_name = cls.parse_name( param )
        param_type = param.get( 'type' )
        if not param_type:
            raise ValueError( "Tool parameter '%s' requires a 'type'" % ( param_name ) )
        elif param_type not in parameter_types:
            raise ValueError( "Tool parameter '%s' uses an unknown type '%s'" % ( param_name, param_type ) )
        else:
            return parameter_types[ param_type ]( tool, param )

    @classmethod
    def parse_name( cls, input_source ):
        name = input_source.get( 'name' )
        if name is None:
            argument = input_source.get( 'argument' )
            if argument:
                name = argument.lstrip( '-' )
            else:
                raise ValueError( "Tool parameter must specify a name." )
        return name


class TextToolParameter( ToolParameter ):
    """
    Parameter that can take on any text value.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch()
    >>> p = TextToolParameter( None, XML( '<param name="_name" type="text" value="default" />' ) )
    >>> print p.name
    _name
    >>> sorted( p.to_dict( trans ).items() )
    [('area', False), ('argument', None), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('model_class', 'TextToolParameter'), ('name', '_name'), ('optional', False), ('refresh_on_change', False), ('type', 'text'), ('value', 'default')]
    """
    def __init__( self, tool, input_source ):
        input_source = ensure_input_source(input_source)
        ToolParameter.__init__( self, tool, input_source )
        self.value = input_source.get( 'value' )
        self.area = input_source.get_bool( 'area', False )

    def to_json( self, value, app, use_security ):
        """Convert a value to a string representation suitable for persisting"""
        if value is None:
            rval = ''
        else:
            rval = util.smart_str( value )
        return rval

    def validate( self, value, trans=None ):
        search = self.type == "text"
        if not ( trans and trans.workflow_building_mode is workflow_building_modes.ENABLED and contains_workflow_parameter(value, search=search) ):
            return super( TextToolParameter, self ).validate( value, trans )

    def get_initial_value( self, trans, other_values ):
        return self.value

    def to_dict( self, trans, other_values={} ):
        d = super(TextToolParameter, self).to_dict(trans)
        d['area'] = self.area
        return d


class IntegerToolParameter( TextToolParameter ):
    """
    Parameter that takes an integer value.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch( history=Bunch(), workflow_building_mode=True )
    >>> p = IntegerToolParameter( None, XML( '<param name="_name" type="integer" value="10" />' ) )
    >>> print p.name
    _name
    >>> sorted( p.to_dict( trans ).items() )
    [('area', False), ('argument', None), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('max', None), ('min', None), ('model_class', 'IntegerToolParameter'), ('name', '_name'), ('optional', False), ('refresh_on_change', False), ('type', 'integer'), ('value', '10')]
    >>> type( p.from_json( "10", trans ) )
    <type 'int'>
    >>> type( p.from_json( "_string", trans ) )
    Traceback (most recent call last):
        ...
    ValueError: An integer or workflow parameter e.g. ${name} is required
    """

    dict_collection_visible_keys = ToolParameter.dict_collection_visible_keys + ( 'min', 'max' )

    def __init__( self, tool, input_source ):
        input_source = ensure_input_source(input_source)
        TextToolParameter.__init__( self, tool, input_source )
        if self.value:
            try:
                int( self.value )
            except:
                raise ValueError( "An integer is required" )
        elif self.value is None and not self.optional:
            raise ValueError( "The settings for the field named '%s' require a 'value' setting and optionally a default value which must be an integer" % self.name )
        self.min = input_source.get( 'min' )
        self.max = input_source.get( 'max' )
        if self.min:
            try:
                self.min = int( self.min )
            except:
                raise ValueError( "An integer is required" )
        if self.max:
            try:
                self.max = int( self.max )
            except:
                raise ValueError( "An integer is required" )
        if self.min is not None or self.max is not None:
            self.validators.append( validation.InRangeValidator( None, self.min, self.max ) )

    def from_json( self, value, trans, other_values={} ):
        try:
            return int( value )
        except:
            if contains_workflow_parameter( value ) and trans.workflow_building_mode is workflow_building_modes.ENABLED:
                return value
            if not value and self.optional:
                return ""
            if trans.workflow_building_mode is workflow_building_modes.ENABLED:
                raise ValueError( "An integer or workflow parameter e.g. ${name} is required" )
            else:
                raise ValueError( "An integer is required" )

    def to_python( self, value, app ):
        try:
            return int( value )
        except Exception as err:
            if contains_workflow_parameter(value):
                return value
            if not value and self.optional:
                return None
            raise err

    def get_initial_value( self, trans, other_values ):
        if self.value:
            return int( self.value )
        else:
            return None


class FloatToolParameter( TextToolParameter ):
    """
    Parameter that takes a real number value.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch( history=Bunch(), workflow_building_mode=True )
    >>> p = FloatToolParameter( None, XML( '<param name="_name" type="float" value="3.141592" />' ) )
    >>> print p.name
    _name
    >>> sorted( p.to_dict( trans ).items() )
    [('area', False), ('argument', None), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('max', None), ('min', None), ('model_class', 'FloatToolParameter'), ('name', '_name'), ('optional', False), ('refresh_on_change', False), ('type', 'float'), ('value', '3.141592')]
    >>> type( p.from_json( "36.1", trans ) )
    <type 'float'>
    >>> type( p.from_json( "_string", trans ) )
    Traceback (most recent call last):
        ...
    ValueError: A real number or workflow parameter e.g. ${name} is required
    """

    dict_collection_visible_keys = ToolParameter.dict_collection_visible_keys + ( 'min', 'max' )

    def __init__( self, tool, input_source ):
        input_source = ensure_input_source(input_source)
        TextToolParameter.__init__( self, tool, input_source )
        self.min = input_source.get( 'min' )
        self.max = input_source.get( 'max' )
        if self.value:
            try:
                float( self.value )
            except:
                raise ValueError( "A real number is required" )
        elif self.value is None and not self.optional:
            raise ValueError( "The settings for this field require a 'value' setting and optionally a default value which must be a real number" )
        if self.min:
            try:
                self.min = float( self.min )
            except:
                raise ValueError( "A real number is required" )
        if self.max:
            try:
                self.max = float( self.max )
            except:
                raise ValueError( "A real number is required" )
        if self.min is not None or self.max is not None:
            self.validators.append( validation.InRangeValidator( None, self.min, self.max ) )

    def from_json( self, value, trans, other_values={} ):
        try:
            return float( value )
        except:
            if contains_workflow_parameter( value ) and trans.workflow_building_mode is workflow_building_modes.ENABLED:
                return value
            if not value and self.optional:
                return ""
            if trans and trans.workflow_building_mode is workflow_building_modes.ENABLED:
                raise ValueError( "A real number or workflow parameter e.g. ${name} is required" )
            else:
                raise ValueError( "A real number is required" )

    def to_python( self, value, app ):
        try:
            return float( value )
        except Exception as err:
            if contains_workflow_parameter( value ):
                return value
            if not value and self.optional:
                return None
            raise err

    def get_initial_value( self, trans, other_values ):
        try:
            return float( self.value )
        except:
            return None


class BooleanToolParameter( ToolParameter ):
    """
    Parameter that takes one of two values.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch( history=Bunch() )
    >>> p = BooleanToolParameter( None, XML( '<param name="_name" type="boolean" checked="yes" truevalue="_truevalue" falsevalue="_falsevalue" />' ) )
    >>> print p.name
    _name
    >>> sorted( p.to_dict( trans ).items() )
    [('argument', None), ('falsevalue', '_falsevalue'), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('model_class', 'BooleanToolParameter'), ('name', '_name'), ('optional', False), ('refresh_on_change', False), ('truevalue', '_truevalue'), ('type', 'boolean'), ('value', True)]
    >>> print p.from_json( 'true' )
    True
    >>> print p.to_param_dict_string( True )
    _truevalue
    >>> print p.from_json( 'false' )
    False
    >>> print p.to_param_dict_string( False )
    _falsevalue
    """
    def __init__( self, tool, input_source ):
        input_source = ensure_input_source(input_source)
        ToolParameter.__init__( self, tool, input_source )
        self.truevalue = input_source.get( 'truevalue', 'true' )
        self.falsevalue = input_source.get( 'falsevalue', 'false' )
        self.checked = input_source.get_bool( 'checked', False )

    def from_json( self, value, trans=None, other_values={} ):
        return self.to_python( value )

    def to_python( self, value, app=None ):
        return ( value in [ True, 'True', 'true' ] )

    def to_json( self, value, app, use_security ):
        if self.to_python( value, app ):
            return 'true'
        else:
            return 'false'

    def get_initial_value( self, trans, other_values ):
        return self.checked

    def to_param_dict_string( self, value, other_values={} ):
        if self.to_python( value ):
            return self.truevalue
        else:
            return self.falsevalue

    def to_dict( self, trans, other_values={} ):
        d = super( BooleanToolParameter, self ).to_dict( trans )
        d['value'] = self.checked
        d['truevalue'] = self.truevalue
        d['falsevalue'] = self.falsevalue
        return d

    @property
    def legal_values( self ):
        return [ self.truevalue, self.falsevalue ]


class FileToolParameter( ToolParameter ):
    """
    Parameter that takes an uploaded file as a value.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch( history=Bunch() )
    >>> p = FileToolParameter( None, XML( '<param name="_name" type="file"/>' ) )
    >>> print p.name
    _name
    >>> sorted( p.to_dict( trans ).items() )
    [('argument', None), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('model_class', 'FileToolParameter'), ('name', '_name'), ('optional', False), ('refresh_on_change', False), ('type', 'file')]
    """
    def __init__( self, tool, input_source ):
        input_source = ensure_input_source(input_source)
        ToolParameter.__init__( self, tool, input_source )

    def from_json( self, value, trans=None, other_values={} ):
        # Middleware or proxies may encode files in special ways (TODO: this
        # should be pluggable)
        if type( value ) == dict:
            upload_store = trans.app.config.nginx_upload_store
            assert upload_store, "Request appears to have been processed by nginx_upload_module but Galaxy is not configured to recognize it."
            # Check that the file is in the right location
            local_filename = os.path.abspath( value[ 'path' ] )
            assert local_filename.startswith( upload_store ), "Filename provided by nginx (%s) is not in correct directory (%s)." % (local_filename, upload_store)
            value = dict( filename=value[ "name" ], local_filename=local_filename )
        return value

    def get_required_enctype( self ):
        """
        File upload elements require the multipart/form-data encoding
        """
        return "multipart/form-data"

    def to_json( self, value, app, use_security ):
        if value in [ None, '' ]:
            return None
        elif isinstance( value, string_types ):
            return value
        elif isinstance( value, dict ):
            # or should we jsonify?
            try:
                return value['local_filename']
            except:
                return None
        raise Exception( "FileToolParameter cannot be persisted" )

    def to_python( self, value, app ):
        if value is None:
            return None
        elif isinstance( value, string_types ):
            return value
        else:
            raise Exception( "FileToolParameter cannot be persisted" )

    def get_initial_value( self, trans, other_values ):
        return None


class FTPFileToolParameter( ToolParameter ):
    """
    Parameter that takes a file uploaded via FTP as a value.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch( history=Bunch() )
    >>> p = FTPFileToolParameter( None, XML( '<param name="_name" type="ftpfile"/>' ) )
    >>> print p.name
    _name
    >>> sorted( p.to_dict( trans ).items() )
    [('argument', None), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('model_class', 'FTPFileToolParameter'), ('multiple', True), ('name', '_name'), ('optional', True), ('refresh_on_change', False), ('type', 'ftpfile')]
    """
    def __init__( self, tool, input_source ):
        input_source = ensure_input_source(input_source)
        ToolParameter.__init__( self, tool, input_source )
        self.multiple = input_source.get_bool( 'multiple', True )
        self.optional = input_source.parse_optional( True )
        self.user_ftp_dir = ''

    def get_initial_value( self, trans, other_values ):
        if trans is not None:
            if trans.user is not None:
                self.user_ftp_dir = "%s/" % trans.user_ftp_dir
        return None

    @property
    def visible( self ):
        if self.tool.app.config.ftp_upload_dir is None or self.tool.app.config.ftp_upload_site is None:
            return False
        return True

    def to_param_dict_string( self, value, other_values={} ):
        if value is '':
            return 'None'
        lst = [ '%s%s' % (self.user_ftp_dir, dataset) for dataset in value ]
        if self.multiple:
            return lst
        else:
            return lst[ 0 ]

    def from_json( self, value, trans=None, other_values={} ):
        return self.to_python( value, trans.app, validate=True )

    def to_json( self, value, app, use_security ):
        return self.to_python( value, app )

    def to_python( self, value, app, validate=False ):
        if not isinstance( value, list ):
            value = [ value ]
        lst = []
        for val in value:
            if val in [ None, '' ]:
                lst = []
                break
            if isinstance( val, dict ):
                lst.append( val[ 'name' ] )
            else:
                lst.append( val )
        if len( lst ) == 0:
            if not self.optional and validate:
                raise ValueError( "Please select a valid FTP file." )
            return None
        if validate and self.tool.app.config.ftp_upload_dir is None:
            raise ValueError( "The FTP directory is not configured." )
        return lst

    def to_dict( self, trans, other_values=None ):
        d = super( FTPFileToolParameter, self ).to_dict( trans )
        d[ 'multiple' ] = self.multiple
        return d


class HiddenToolParameter( ToolParameter ):
    """
    Parameter that takes one of two values.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch( history=Bunch() )
    >>> p = HiddenToolParameter( None, XML( '<param name="_name" type="hidden" value="_value"/>' ) )
    >>> print p.name
    _name
    >>> sorted( p.to_dict( trans ).items() )
    [('argument', None), ('help', ''), ('hidden', True), ('is_dynamic', False), ('label', ''), ('model_class', 'HiddenToolParameter'), ('name', '_name'), ('optional', False), ('refresh_on_change', False), ('type', 'hidden'), ('value', '_value')]
    """
    def __init__( self, tool, input_source ):
        input_source = ensure_input_source( input_source )
        ToolParameter.__init__( self, tool, input_source )
        self.value = input_source.get( 'value' )
        self.hidden = True

    def get_initial_value( self, trans, other_values ):
        return self.value

    def get_label( self ):
        return None


class ColorToolParameter( ToolParameter ):
    """
    Parameter that stores a color.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch( history=Bunch() )
    >>> p = ColorToolParameter( None, XML( '<param name="_name" type="color" value="#ffffff"/>' ) )
    >>> print p.name
    _name
    >>> print p.to_param_dict_string( "#fdeada" )
    #fdeada
    >>> sorted( p.to_dict( trans ).items() )
    [('argument', None), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('model_class', 'ColorToolParameter'), ('name', '_name'), ('optional', False), ('refresh_on_change', False), ('type', 'color'), ('value', '#ffffff')]
    >>> p = ColorToolParameter( None, XML( '<param name="_name" type="color" value="#ffffff" rgb="True"/>' ) )
    >>> print p.to_param_dict_string( "#fdeada" )
    (253, 234, 218)
    >>> print p.to_param_dict_string( None )
    Traceback (most recent call last):
        ...
    ValueError: Failed to convert 'None' to RGB.
    """
    def __init__( self, tool, input_source ):
        input_source = ensure_input_source( input_source )
        ToolParameter.__init__( self, tool, input_source )
        self.value = input_source.get( 'value', '#fdeada' )
        self.rgb = input_source.get( 'rgb', False )

    def get_initial_value( self, trans, other_values ):
        return self.value.lower()

    def to_param_dict_string( self, value, other_values={} ):
        if self.rgb:
            try:
                return str( tuple( int( value.lstrip( '#' )[ i : i + 2 ], 16 ) for i in ( 0, 2, 4 ) ) )
            except Exception:
                raise ValueError( "Failed to convert \'%s\' to RGB." % value )
        return str( value )


class BaseURLToolParameter( HiddenToolParameter ):
    """
    Returns a parameter that contains its value prepended by the
    current server base url. Used in all redirects.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch( history=Bunch() )
    >>> p = BaseURLToolParameter( None, XML( '<param name="_name" type="base_url" value="_value"/>' ) )
    >>> print p.name
    _name
    >>> sorted( p.to_dict( trans ).items() )
    [('argument', None), ('help', ''), ('hidden', True), ('is_dynamic', False), ('label', ''), ('model_class', 'BaseURLToolParameter'), ('name', '_name'), ('optional', False), ('refresh_on_change', False), ('type', 'base_url'), ('value', '_value')]
    """
    def __init__( self, tool, input_source ):
        input_source = ensure_input_source( input_source )
        super( BaseURLToolParameter, self ).__init__( tool, input_source )
        self.value = input_source.get( 'value', '' )

    def get_initial_value( self, trans, other_values ):
        return self._get_value()

    def from_json( self, value=None, trans=None, other_values={} ):
        return self._get_value()

    def _get_value( self ):
        try:
            return url_for( self.value, qualified=True )
        except Exception as e:
            log.debug( 'Url creation failed for "%s": %s', self.name, e )
            return self.value

    def to_dict( self, trans, other_values={} ):
        d = super( BaseURLToolParameter, self ).to_dict( trans )
        d[ 'value' ] = self._get_value()
        return d


class SelectToolParameter( ToolParameter ):
    """
    Parameter that takes on one (or many) or a specific set of values.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch( history=Bunch() )
    >>> p = SelectToolParameter( None, XML(
    ... '''
    ... <param name="_name" type="select">
    ...     <option value="x">x_label</option>
    ...     <option value="y" selected="true">y_label</option>
    ...     <option value="z">z_label</option>
    ... </param>
    ... ''' ) )
    >>> print p.name
    _name
    >>> sorted( p.to_dict( trans ).items() )
    [('argument', None), ('display', None), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('model_class', 'SelectToolParameter'), ('multiple', False), ('name', '_name'), ('optional', False), ('options', [('x_label', 'x', False), ('y_label', 'y', True), ('z_label', 'z', False)]), ('refresh_on_change', False), ('type', 'select'), ('value', 'y')]
    >>> p = SelectToolParameter( None, XML(
    ... '''
    ... <param name="_name" type="select" multiple="true">
    ...     <option value="x">x_label</option>
    ...     <option value="y" selected="true">y_label</option>
    ...     <option value="z" selected="true">z_label</option>
    ... </param>
    ... ''' ) )
    >>> print p.name
    _name
    >>> sorted( p.to_dict( trans ).items() )
    [('argument', None), ('display', None), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('model_class', 'SelectToolParameter'), ('multiple', True), ('name', '_name'), ('optional', True), ('options', [('x_label', 'x', False), ('y_label', 'y', True), ('z_label', 'z', True)]), ('refresh_on_change', False), ('type', 'select'), ('value', 'z')]
    >>> print p.to_param_dict_string( ["y", "z"] )
    y,z
    """
    def __init__( self, tool, input_source, context=None ):
        input_source = ensure_input_source( input_source )
        ToolParameter.__init__( self, tool, input_source )
        self.multiple = input_source.get_bool( 'multiple', False )
        # Multiple selects are optional by default, single selection is the inverse.
        self.optional = input_source.parse_optional( self.multiple )
        self.display = input_source.get( 'display', None )
        self.separator = input_source.get( 'separator', ',' )
        self.legal_values = set()
        self.dynamic_options = input_source.get( 'dynamic_options', None )
        self.options = parse_dynamic_options( self, input_source )
        if self.options is not None:
            for validator in self.options.validators:
                self.validators.append( validator )
        if self.dynamic_options is None and self.options is None:
            self.static_options = input_source.parse_static_options()
            for (title, value, selected) in self.static_options:
                self.legal_values.add( value )
        self.is_dynamic = ( ( self.dynamic_options is not None ) or ( self.options is not None ) )

    def _get_dynamic_options_call_other_values( self, trans, other_values ):
        call_other_values = ExpressionContext( { '__trans__': trans } )
        if other_values:
            call_other_values.parent = other_values.parent
            call_other_values.update( other_values.dict )
        return call_other_values

    def get_options( self, trans, other_values ):
        if self.options:
            return self.options.get_options( trans, other_values )
        elif self.dynamic_options:
            call_other_values = self._get_dynamic_options_call_other_values( trans, other_values )
            try:
                return eval( self.dynamic_options, self.tool.code_namespace, call_other_values )
            except Exception as e:
                log.debug( "Error determining dynamic options for parameter '%s' in tool '%s':", self.name, self.tool.id, exc_info=e )
                return []
        else:
            return self.static_options

    def get_legal_values( self, trans, other_values ):
        if self.options:
            return set( v for _, v, _ in self.options.get_options( trans, other_values ) )
        elif self.dynamic_options:
            try:
                call_other_values = self._get_dynamic_options_call_other_values( trans, other_values )
                return set( v for _, v, _ in eval( self.dynamic_options, self.tool.code_namespace, call_other_values ) )
            except Exception as e:
                log.debug( "Determining legal values failed for '%s': %s", self.name, e )
                return set()
        else:
            return self.legal_values

    def from_json( self, value, trans, other_values={} ):
        legal_values = self.get_legal_values( trans, other_values )
        workflow_building_mode = trans.workflow_building_mode
        for context_value in other_values.values():
            if isinstance( context_value, RuntimeValue ):
                workflow_building_mode = True
                break
        if len( list( legal_values ) ) == 0 and workflow_building_mode:
            if self.multiple:
                # While it is generally allowed that a select value can be '',
                # we do not allow this to be the case in a dynamically
                # generated multiple select list being set in workflow building
                # mode we instead treat '' as 'No option Selected' (None)
                if value == '':
                    value = None
                else:
                    if isinstance( value, string_types ):
                        # Split on all whitespace. This not only provides flexibility
                        # in interpreting values but also is needed because many browsers
                        # use \r\n to separate lines.
                        value = value.split()
            return value
        if ( not legal_values or value is None ) and self.optional:
            return None
        if not legal_values:
            raise ValueError( "Parameter %s requires a value, but has no legal values defined." % self.name )
        if isinstance( value, list ):
            if not self.multiple:
                raise ValueError( "Multiple values provided but parameter %s is not expecting multiple values." % self.name )
            rval = []
            for v in value:
                if v not in legal_values:
                    raise ValueError( "An invalid option was selected for %s, %r, please verify." % ( self.name, v ) )
                rval.append( v )
            return rval
        else:
            value_is_none = ( value == "None" and "None" not in legal_values )
            if value_is_none or not value:
                if self.multiple:
                    if self.optional:
                        return []
                    else:
                        raise ValueError( "No option was selected for %s but input is not optional." % self.name )
            if value not in legal_values:
                raise ValueError( "An invalid option was selected for %s, %r, please verify." % ( self.name, value ) )
            return value

    def to_param_dict_string( self, value, other_values={} ):
        if value is None:
            return "None"
        if isinstance( value, list ):
            if not self.multiple:
                raise ValueError( "Multiple values provided but parameter %s is not expecting multiple values." % self.name )
            value = list(map( str, value ))
        else:
            value = str( value )
        if self.tool is None or self.tool.options.sanitize:
            if self.sanitizer:
                value = self.sanitizer.sanitize_param( value )
            else:
                value = sanitize_param( value )
        if isinstance( value, list ):
            value = self.separator.join( value )
        return value

    def to_json( self, value, app, use_security ):
        return value

    def get_initial_value( self, trans, other_values ):
        options = list( self.get_options( trans, other_values ) )
        if len(options) == 0 and trans.workflow_building_mode:
            return None
        value = [ optval for _, optval, selected in options if selected ]
        if len( value ) == 0:
            if not self.optional and not self.multiple and options:
                # Nothing selected, but not optional and not a multiple select, with some values,
                # so we have to default to something (the HTML form will anyway)
                value = options[ 0 ][ 1 ]
            else:
                value = None
        elif len( value ) == 1:
            value = value[0]
        return value

    def value_to_display_text( self, value, app ):
        if not isinstance( value, list ):
            value = [ value ]
        # FIXME: Currently only translating values back to labels if they
        #        are not dynamic
        if self.is_dynamic:
            rval = map( str, value )
        else:
            options = list( self.static_options )
            rval = []
            for t, v, s in options:
                if v in value:
                    rval.append( t )
        if rval:
            return "\n".join( rval )
        return "Nothing selected."

    def get_dependencies( self ):
        """
        Get the *names* of the other params this param depends on.
        """
        if self.options:
            return self.options.get_dependency_names()
        else:
            return []

    def to_dict( self, trans, other_values={} ):
        d = super( SelectToolParameter, self ).to_dict( trans )

        # Get options, value.
        options = self.get_options( trans, other_values )
        d[ 'options' ] = options
        if options:
            value = options[ 0 ][ 1 ]
            for option in options:
                if option[ 2 ]:
                    # Found selected option.
                    value = option[ 1 ]
            d[ 'value' ] = value

        d[ 'display' ] = self.display
        d[ 'multiple' ] = self.multiple
        return d


class GenomeBuildParameter( SelectToolParameter ):
    """
    Select list that sets the last used genome build for the current history as "selected".

    >>> # Create a mock transaction with 'hg17' as the current build
    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch( history=Bunch( genome_build='hg17' ), db_builds=util.read_dbnames( None ) )
    >>> p = GenomeBuildParameter( None, XML( '<param name="_name" type="genomebuild" value="hg17" />' ) )
    >>> print p.name
    _name
    >>> d = p.to_dict( trans )
    >>> o = d[ 'options' ]
    >>> [ i for i in o if i[ 2 ] == True ]
    [('Human May 2004 (NCBI35/hg17) (hg17)', 'hg17', True)]
    >>> [ i for i in o if i[ 1 ] == 'hg18' ]
    [('Human Mar. 2006 (NCBI36/hg18) (hg18)', 'hg18', False)]
    """
    def __init__( self, *args, **kwds ):
        super( GenomeBuildParameter, self ).__init__( *args, **kwds )
        if self.tool:
            self.static_options = [ ( value, key, False ) for key, value in self._get_dbkey_names()]

    def get_options( self, trans, other_values ):
        last_used_build = object()
        if trans.history:
            last_used_build = trans.history.genome_build
        for dbkey, build_name in self._get_dbkey_names( trans=trans ):
            yield build_name, dbkey, ( dbkey == last_used_build )

    def get_legal_values( self, trans, other_values ):
        return set( dbkey for dbkey, _ in self._get_dbkey_names( trans=trans ) )

    def to_dict( self, trans, other_values={} ):
        # skip SelectToolParameter (the immediate parent) bc we need to get options in a different way here
        d = ToolParameter.to_dict( self, trans )

        # Get options, value - options is a generator here, so compile to list
        options = list( self.get_options( trans, {} ) )
        value = options[0][1]
        for option in options:
            if option[2]:
                # Found selected option.
                value = option[1]

        d.update({
            'options'   : options,
            'value'     : value,
            'display'   : self.display,
            'multiple'  : self.multiple,
        })

        return d

    def _get_dbkey_names( self, trans=None ):
        if not self.tool:
            # Hack for unit tests, since we have no tool
            return util.read_dbnames( None )
        return self.tool.app.genome_builds.get_genome_build_names( trans=trans )


class ColumnListParameter( SelectToolParameter ):
    """
    Select list that consists of either the total number of columns or only
    those columns that contain numerical values in the associated DataToolParameter.

    # TODO: we need better testing here, but not sure how to associate a DatatoolParameter with a ColumnListParameter
    # from a twill perspective...

    >>> # Mock up a history (not connected to database)
    >>> from galaxy.model import History, HistoryDatasetAssociation
    >>> from galaxy.util.bunch import Bunch
    >>> from galaxy.model.mapping import init
    >>> sa_session = init( "/tmp", "sqlite:///:memory:", create_tables=True ).session
    >>> hist = History()
    >>> sa_session.add( hist )
    >>> sa_session.flush()
    >>> hda = hist.add_dataset( HistoryDatasetAssociation( id=1, extension='interval', create_dataset=True, sa_session=sa_session ) )
    >>> dtp =  DataToolParameter( None, XML( '<param name="blah" type="data" format="interval"/>' ) )
    >>> print dtp.name
    blah
    >>> clp = ColumnListParameter ( None, XML( '<param name="numerical_column" type="data_column" data_ref="blah" numerical="true"/>' ) )
    >>> print clp.name
    numerical_column
    """
    def __init__( self, tool, input_source ):
        input_source = ensure_input_source( input_source )
        SelectToolParameter.__init__( self, tool, input_source )
        self.tool = tool
        self.numerical = input_source.get_bool( "numerical", False )
        self.optional = input_source.parse_optional( False )
        self.accept_default = input_source.get_bool( "accept_default", False )
        if self.accept_default:
            self.optional = True
        self.data_ref = input_source.get( "data_ref", None )
        self.ref_input = None
        # Legacy style default value specification...
        self.default_value = input_source.get( "default_value", None )
        if self.default_value is None:
            # Newer style... more in line with other parameters.
            self.default_value = input_source.get( "value", None )
        if self.default_value is not None:
            self.default_value = ColumnListParameter._strip_c( self.default_value )
        self.is_dynamic = True
        self.usecolnames = input_source.get_bool( "use_header_names", False )

    def from_json( self, value, trans, other_values={} ):
        """
        Label convention prepends column number with a 'c', but tool uses the integer. This
        removes the 'c' when entered into a workflow.
        """
        if self.multiple:
            # split on newline and ,
            if isinstance( value, list ) or isinstance( value, string_types ):
                column_list = []
                if not isinstance( value, list ):
                    value = value.split( '\n' )
                for column in value:
                    for column2 in str( column ).split( ',' ):
                        column2 = column2.strip()
                        if column2:
                            column_list.append( column2 )
                value = list(map( ColumnListParameter._strip_c, column_list ))
            else:
                value = []
        else:
            if value:
                value = ColumnListParameter._strip_c( value )
            else:
                value = None
        if not value and self.accept_default:
            value = self.default_value or '1'
            return [ value ] if self.multiple else value
        return super( ColumnListParameter, self ).from_json( value, trans, other_values )

    @staticmethod
    def _strip_c(column):
        if isinstance(column, string_types):
            if column.startswith( 'c' ):
                column = column.strip().lower()[1:]
        return column

    def get_column_list( self, trans, other_values ):
        """
        Generate a select list containing the columns of the associated
        dataset (if found).
        """
        # Get the value of the associated data reference (a dataset)
        dataset = other_values.get( self.data_ref, None )
        # Check if a dataset is selected
        if not dataset:
            return []
        column_list = None
        for dataset in util.listify( dataset ):
            # Use representative dataset if a dataset collection is parsed
            if isinstance( dataset, trans.app.model.HistoryDatasetCollectionAssociation ):
                dataset = dataset.to_hda_representative()
            # Columns can only be identified if metadata is available
            if not hasattr( dataset, 'metadata' ) or not hasattr( dataset.metadata, 'columns' ) or not dataset.metadata.columns:
                return []
            # Build up possible columns for this dataset
            this_column_list = []
            if self.numerical:
                # If numerical was requested, filter columns based on metadata
                for i, col in enumerate( dataset.metadata.column_types ):
                    if col == 'int' or col == 'float':
                        this_column_list.append( str( i + 1 ) )
            else:
                for i in range( 0, dataset.metadata.columns ):
                    this_column_list.append( str( i + 1 ) )
            # Take the intersection of these columns with the other columns.
            if column_list is None:
                column_list = this_column_list
            else:
                column_list = [c for c in column_list if c in this_column_list]
        return column_list

    def get_options( self, trans, other_values ):
        """
        Show column labels rather than c1..cn if use_header_names=True
        """
        options = []
        if self.usecolnames:  # read first row - assume is a header with metadata useful for making good choices
            dataset = other_values.get( self.data_ref, None )
            try:
                head = open( dataset.get_file_name(), 'r' ).readline()
                cnames = head.rstrip().split( '\t' )
                column_list = [ ( '%d' % ( i + 1 ), 'c%d: %s' % ( i + 1, x ) ) for i, x in enumerate( cnames ) ]
                if self.numerical:  # If numerical was requested, filter columns based on metadata
                    if hasattr( dataset, 'metadata' ) and hasattr( dataset.metadata, 'column_types' ):
                        if len( dataset.metadata.column_types ) >= len( cnames ):
                            numerics = [ i for i, x in enumerate( dataset.metadata.column_types ) if x in [ 'int', 'float' ] ]
                            column_list = [ column_list[ i ] for i in numerics ]
            except:
                column_list = self.get_column_list( trans, other_values )
        else:
            column_list = self.get_column_list( trans, other_values )
        for col in column_list:
            if isinstance( col, tuple ) and len( col ) == 2:
                options.append( ( col[ 1 ], col[ 0 ], False ) )
            else:
                options.append( ( 'Column: ' + col, col, False ) )
        return options

    def get_initial_value( self, trans, other_values ):
        if self.default_value is not None:
            return self.default_value
        return SelectToolParameter.get_initial_value( self, trans, other_values )

    def get_legal_values( self, trans, other_values ):
        if self.data_ref not in other_values:
            raise ValueError( "Value for associated data reference not found (data_ref)." )
        return set( self.get_column_list( trans, other_values ) )

    def get_dependencies( self ):
        return [ self.data_ref ]

    def to_dict( self, trans, other_values={} ):
        d = super( ColumnListParameter, self ).to_dict( trans, other_values=other_values)
        d[ 'data_ref' ] = self.data_ref
        d[ 'numerical' ] = self.numerical
        return d


class DrillDownSelectToolParameter( SelectToolParameter ):
    """
    Parameter that takes on one (or many) of a specific set of values.
    Creating a hierarchical select menu, which allows users to 'drill down' a tree-like set of options.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch( history=Bunch( genome_build='hg17' ), db_builds=util.read_dbnames( None ) )
    >>> p = DrillDownSelectToolParameter( None, XML(
    ... '''
    ... <param name="_name" type="drill_down" display="checkbox" hierarchy="recurse" multiple="true">
    ...   <options>
    ...    <option name="Heading 1" value="heading1">
    ...        <option name="Option 1" value="option1"/>
    ...        <option name="Option 2" value="option2"/>
    ...        <option name="Heading 2" value="heading2">
    ...          <option name="Option 3" value="option3"/>
    ...          <option name="Option 4" value="option4"/>
    ...        </option>
    ...    </option>
    ...    <option name="Option 5" value="option5"/>
    ...   </options>
    ... </param>
    ... ''' ) )
    >>> print p.name
    _name
    >>> d = p.to_dict( trans )
    >>> assert d[ 'multiple' ] == True
    >>> assert d[ 'display' ] == 'checkbox'
    >>> assert d[ 'options' ][ 0 ][ 'name' ] == 'Heading 1'
    >>> assert d[ 'options' ][ 0 ][ 'value' ] == 'heading1'
    >>> assert d[ 'options' ][ 0 ][ 'options' ][ 0 ][ 'name' ] == 'Option 1'
    >>> assert d[ 'options' ][ 0 ][ 'options' ][ 0 ][ 'value' ] == 'option1'
    >>> assert d[ 'options' ][ 0 ][ 'options' ][ 1 ][ 'name' ] == 'Option 2'
    >>> assert d[ 'options' ][ 0 ][ 'options' ][ 1 ][ 'value' ] == 'option2'
    >>> assert d[ 'options' ][ 0 ][ 'options' ][ 2 ][ 'name' ] == 'Heading 2'
    >>> assert d[ 'options' ][ 0 ][ 'options' ][ 2 ][ 'value' ] == 'heading2'
    >>> assert d[ 'options' ][ 0 ][ 'options' ][ 2 ][ 'options' ][ 0 ][ 'name' ] == 'Option 3'
    >>> assert d[ 'options' ][ 0 ][ 'options' ][ 2 ][ 'options' ][ 0 ][ 'value' ] == 'option3'
    >>> assert d[ 'options' ][ 0 ][ 'options' ][ 2 ][ 'options' ][ 1 ][ 'name' ] == 'Option 4'
    >>> assert d[ 'options' ][ 0 ][ 'options' ][ 2 ][ 'options' ][ 1 ][ 'value' ] == 'option4'
    >>> assert d[ 'options' ][ 1 ][ 'name' ] == 'Option 5'
    >>> assert d[ 'options' ][ 1 ][ 'value' ] == 'option5'
    """
    def __init__( self, tool, input_source, context=None ):
        input_source = ensure_input_source( input_source )

        def recurse_option_elems( cur_options, option_elems ):
            for option_elem in option_elems:
                selected = string_as_bool( option_elem.get( 'selected', False ) )
                cur_options.append( { 'name': option_elem.get( 'name' ), 'value': option_elem.get( 'value' ), 'options': [], 'selected': selected  } )
                recurse_option_elems( cur_options[-1]['options'], option_elem.findall( 'option' ) )
        ToolParameter.__init__( self, tool, input_source )
        # TODO: abstract XML out of here - so non-XML InputSources can
        # specify DrillDown parameters.
        elem = input_source.elem()
        self.multiple = string_as_bool( elem.get( 'multiple', False ) )
        self.display = elem.get( 'display', None )
        self.hierarchy = elem.get( 'hierarchy', 'exact' )  # exact or recurse
        self.separator = elem.get( 'separator', ',' )
        from_file = elem.get( 'from_file', None )
        if from_file:
            if not os.path.isabs( from_file ):
                from_file = os.path.join( tool.app.config.tool_data_path, from_file )
            elem = XML( "<root>%s</root>" % open( from_file ).read() )
        self.dynamic_options = elem.get( 'dynamic_options', None )
        if self.dynamic_options:
            self.is_dynamic = True
        self.options = []
        self.filtered = {}
        if elem.find( 'filter' ):
            self.is_dynamic = True
            for filter in elem.findall( 'filter' ):
                # currently only filtering by metadata key matching input file is allowed
                if filter.get( 'type' ) == 'data_meta':
                    if filter.get( 'data_ref' ) not in self.filtered:
                        self.filtered[filter.get( 'data_ref' )] = {}
                    if filter.get( 'meta_key' ) not in self.filtered[filter.get( 'data_ref' )]:
                        self.filtered[filter.get( 'data_ref' )][filter.get( 'meta_key' )] = {}
                    if filter.get( 'value' ) not in self.filtered[filter.get( 'data_ref' )][filter.get( 'meta_key' )]:
                        self.filtered[filter.get( 'data_ref' )][filter.get( 'meta_key' )][filter.get( 'value' )] = []
                    recurse_option_elems( self.filtered[filter.get( 'data_ref' )][filter.get( 'meta_key' )][filter.get( 'value' )], filter.find( 'options' ).findall( 'option' ) )
        elif not self.dynamic_options:
            recurse_option_elems( self.options, elem.find( 'options' ).findall( 'option' ) )

    def _get_options_from_code( self, trans=None, value=None, other_values=None ):
        assert self.dynamic_options, Exception( "dynamic_options was not specifed" )
        call_other_values = ExpressionContext({ '__trans__': trans, '__value__': value })
        if other_values:
            call_other_values.parent = other_values.parent
            call_other_values.update( other_values.dict )
        try:
            return eval( self.dynamic_options, self.tool.code_namespace, call_other_values )
        except Exception:
            return []

    def get_options( self, trans=None, value=None, other_values={} ):
        if self.is_dynamic:
            if self.dynamic_options:
                options = self._get_options_from_code( trans=trans, value=value, other_values=other_values )
            else:
                options = []
            for filter_key, filter_value in self.filtered.items():
                dataset = other_values.get(filter_key)
                if dataset.__class__.__name__.endswith( "DatasetFilenameWrapper" ):  # this is a bad way to check for this, but problems importing class ( due to circular imports? )
                    dataset = dataset.dataset
                if dataset:
                    for meta_key, meta_dict in filter_value.items():
                        if hasattr( dataset, 'metadata' ) and hasattr( dataset.metadata, 'spec' ):
                            check_meta_val = dataset.metadata.spec[ meta_key ].param.to_string( dataset.metadata.get( meta_key ) )
                            if check_meta_val in meta_dict:
                                options.extend( meta_dict[ check_meta_val ] )
            return options
        return self.options

    def get_legal_values( self, trans, other_values ):
        def recurse_options( legal_values, options ):
            for option in options:
                legal_values.append( option['value'] )
                recurse_options( legal_values, option['options'] )
        legal_values = []
        recurse_options( legal_values, self.get_options( trans=trans, other_values=other_values ) )
        return legal_values

    def from_json( self, value, trans, other_values={} ):
        legal_values = self.get_legal_values( trans, other_values )
        if len( list( legal_values ) ) == 0 and trans.workflow_building_mode:
            if self.multiple:
                if value == '':  # No option selected
                    value = None
                else:
                    value = value.split( "\n" )
            return value
        if not value and not self.optional:
            raise ValueError( "An invalid option was selected for %s, please verify." % (self.name) )
        if not value:
            return None
        if not isinstance( value, list ):
            value = [ value ]
        if len( value ) > 1 and not self.multiple:
            raise ValueError( "Multiple values provided but parameter %s is not expecting multiple values." % self.name )
        rval = []
        if not legal_values:
            raise ValueError( "Parameter %s requires a value, but has no legal values defined." % self.name )
        for val in value:
            if val not in legal_values:
                raise ValueError( "An invalid option was selected for %s, %r, please verify" % ( self.name, val ) )
            rval.append( val )
        return rval

    def to_param_dict_string( self, value, other_values={} ):
        def get_options_list( value ):
            def get_base_option( value, options ):
                for option in options:
                    if value == option['value']:
                        return option
                    rval = get_base_option( value, option['options'] )
                    if rval:
                        return rval
                return None  # not found

            def recurse_option( option_list, option ):
                if not option['options']:
                    option_list.append( option['value'] )
                else:
                    for opt in option['options']:
                        recurse_option( option_list, opt )
            rval = []
            recurse_option( rval, get_base_option( value, self.get_options( other_values=other_values ) ) )
            return rval or [value]

        if value is None:
            return "None"
        rval = []
        if self.hierarchy == "exact":
            rval = value
        else:
            for val in value:
                options = get_options_list( val )
                rval.extend( options )
        if len( rval ) > 1 and not self.multiple:
            raise ValueError( "Multiple values provided but parameter %s is not expecting multiple values." % self.name )
        rval = self.separator.join( rval )
        if self.tool is None or self.tool.options.sanitize:
            if self.sanitizer:
                rval = self.sanitizer.sanitize_param( rval )
            else:
                rval = sanitize_param( rval )
        return rval

    def get_initial_value( self, trans, other_values ):
        def recurse_options( initial_values, options ):
            for option in options:
                if option['selected']:
                    initial_values.append( option['value'] )
                recurse_options( initial_values, option['options'] )
        # More working around dynamic options for workflow
        options = self.get_options( trans=trans, other_values=other_values )
        if len( list( options ) ) == 0 and trans.workflow_building_mode:
            return None
        initial_values = []
        recurse_options( initial_values, options )
        if len( initial_values ) == 0:
            initial_values = None
        return initial_values

    def value_to_display_text( self, value, app ):
        def get_option_display( value, options ):
            for option in options:
                if value == option['value']:
                    return option['name']
                rval = get_option_display( value, option['options'] )
                if rval:
                    return rval
            return None  # not found
        if not value:
            value = []
        elif not isinstance( value, list ):
            value = [ value ]
        # FIXME: Currently only translating values back to labels if they
        #        are not dynamic
        if self.is_dynamic:
            if value:
                if isinstance( value, list ):
                    rval = value
                else:
                    rval = [ value ]
            else:
                rval = []
        else:
            rval = []
            for val in value:
                rval.append( get_option_display( val, self.options ) or val )
        if rval:
            return "\n".join( map( str, rval ) )
        return "Nothing selected."

    def get_dependencies( self ):
        """
        Get the *names* of the other params this param depends on.
        """
        return list(self.filtered.keys())

    def to_dict( self, trans, other_values={} ):
        # skip SelectToolParameter (the immediate parent) bc we need to get options in a different way here
        d = ToolParameter.to_dict( self, trans )
        d[ 'options' ] = self.get_options( trans=trans, other_values=other_values )
        d[ 'display' ] = self.display
        d[ 'multiple' ] = self.multiple
        return d


class BaseDataToolParameter( ToolParameter ):

    def __init__( self, tool, input_source, trans ):
        super(BaseDataToolParameter, self).__init__( tool, input_source )
        self.refresh_on_change = True

    def _datatypes_registery( self, trans, tool ):
        # Find datatypes_registry
        if tool is None:
            if trans:
                # Must account for "Input Dataset" types, which while not a tool still need access to the real registry.
                # A handle to the transaction (and thus app) will be given by the module.
                datatypes_registry = trans.app.datatypes_registry
            else:
                # This occurs for things such as unit tests
                import galaxy.datatypes.registry
                datatypes_registry = galaxy.datatypes.registry.Registry()
                datatypes_registry.load_datatypes()
        else:
            datatypes_registry = tool.app.datatypes_registry
        return datatypes_registry

    def _parse_formats( self, trans, tool, input_source ):
        datatypes_registry = self._datatypes_registery( trans, tool )

        # Build tuple of classes for supported data formats
        formats = []
        self.extensions = input_source.get( 'format', 'data' ).split( "," )
        normalized_extensions = [extension.strip().lower() for extension in self.extensions]
        for extension in normalized_extensions:
            formats.append( datatypes_registry.get_datatype_by_extension( extension ) )
        self.formats = formats

    def _parse_options( self, input_source ):
        # TODO: Enhance dynamic options for DataToolParameters. Currently,
        #       only the special case key='build' of type='data_meta' is
        #       a valid filter
        self.options_filter_attribute = None
        self.options = parse_dynamic_options( self, input_source )
        if self.options:
            # TODO: Abstract away XML handling here.
            options_elem = input_source.elem().find('options')
            self.options_filter_attribute = options_elem.get(  'options_filter_attribute', None )
        self.is_dynamic = self.options is not None

    def get_initial_value( self, trans, other_values ):
        if trans.workflow_building_mode is workflow_building_modes.ENABLED or trans.app.name == 'tool_shed':
            return RuntimeValue()
        if self.optional:
            return None
        history = trans.history
        if history is not None:
            dataset_matcher = DatasetMatcher( trans, self, None, other_values )
            if isinstance( self, DataToolParameter ):
                for hda in reversed( history.active_datasets_children_and_roles ):
                    match = dataset_matcher.hda_match( hda, check_security=False )
                    if match:
                        return match.hda
            else:
                dataset_collection_matcher = DatasetCollectionMatcher( dataset_matcher )
                for hdca in reversed( history.active_dataset_collections ):
                    if dataset_collection_matcher.hdca_match( hdca, reduction=self.multiple ):
                        return hdca

    def to_json( self, value, app, use_security ):
        def single_to_json( value ):
            src = None
            if isinstance( value, dict ) and 'src' in value and 'id' in value:
                return value
            elif isinstance( value, galaxy.model.DatasetCollectionElement ):
                src = 'dce'
            elif isinstance( value, app.model.HistoryDatasetCollectionAssociation ):
                src = 'hdca'
            elif hasattr( value, 'id' ):
                src = 'hda'
            if src is not None:
                return { 'id' : app.security.encode_id( value.id ) if use_security else value.id, 'src' : src }
        if value not in [ None, '', 'None' ]:
            if isinstance( value, list ) and len( value ) > 0:
                values = [ single_to_json( v ) for v in value ]
            else:
                values = [ single_to_json( value ) ]
            return { 'values': values }
        return None

    def to_python( self, value, app ):
        def single_to_python( value ):
            if isinstance( value, dict ) and 'src' in value:
                id = value[ 'id' ] if isinstance( value[ 'id' ], int ) else app.security.decode_id( value[ 'id' ] )
                if value[ 'src' ] == 'dce':
                    return app.model.context.query( app.model.DatasetCollectionElement ).get( id )
                elif value[ 'src' ] == 'hdca':
                    return app.model.context.query( app.model.HistoryDatasetCollectionAssociation ).get( id )
                else:
                    return app.model.context.query( app.model.HistoryDatasetAssociation ).get( id )

        if isinstance( value, dict ) and 'values' in value:
            if hasattr( self, 'multiple' ) and self.multiple is True:
                return [ single_to_python( v ) for v in value[ 'values' ] ]
            elif len( value[ 'values' ] ) > 0:
                return single_to_python( value[ 'values' ][ 0 ] )

        # Handle legacy string values potentially stored in databases
        none_values = [ None, '', 'None' ]
        if value in none_values:
            return None
        if isinstance( value, string_types ) and value.find( ',' ) > -1:
            return [ app.model.context.query( app.model.HistoryDatasetAssociation ).get( int( v ) ) for v in value.split( ',' ) if v not in none_values ]
        elif str( value ).startswith( "__collection_reduce__|" ):
            decoded_id = str( value )[ len( "__collection_reduce__|" ): ]
            if not decoded_id.isdigit():
                decoded_id = app.security.decode_id( decoded_id )
            return app.model.context.query( app.model.HistoryDatasetCollectionAssociation ).get( int( decoded_id ) )
        elif str( value ).startswith( "dce:" ):
            return app.model.context.query( app.model.DatasetCollectionElement ).get( int( value[ len( "dce:" ): ] ) )
        elif str( value ).startswith( "hdca:" ):
            return app.model.context.query( app.model.HistoryDatasetCollectionAssociation ).get( int( value[ len( "hdca:" ): ] ) )
        else:
            return app.model.context.query( app.model.HistoryDatasetAssociation ).get( int( value ) )


class DataToolParameter( BaseDataToolParameter ):
    # TODO, Nate: Make sure the following unit tests appropriately test the dataset security
    # components.  Add as many additional tests as necessary.
    """
    Parameter that takes on one (or many) or a specific set of values.

    TODO: There should be an alternate display that allows single selects to be
          displayed as radio buttons and multiple selects as a set of checkboxes

    TODO: The following must be fixed to test correctly for the new security_check tag in
    the DataToolParameter ( the last test below is broken ) Nate's next pass at the dataset
    security stuff will dramatically alter this anyway.
    """

    def __init__( self, tool, input_source, trans=None):
        input_source = ensure_input_source( input_source )
        super(DataToolParameter, self).__init__( tool, input_source, trans )
        # Add metadata validator
        if not input_source.get_bool( 'no_validation', False ):
            self.validators.append( validation.MetadataValidator() )
        self._parse_formats( trans, tool, input_source )
        self.multiple = input_source.get_bool('multiple', False)
        self.min = input_source.get( 'min' )
        self.max = input_source.get( 'max' )
        if self.min:
            try:
                self.min = int( self.min )
            except:
                raise ValueError( "An integer is required for min property." )
        if self.max:
            try:
                self.max = int( self.max )
            except:
                raise ValueError( "An integer is required for max property." )
        if not self.multiple and (self.min is not None):
            raise ValueError( "Cannot specify min property on single data parameter '%s'. Set multiple=\"true\" to enable this option." % self.name )
        if not self.multiple and (self.max is not None):
            raise ValueError( "Cannot specify max property on single data parameter '%s'. Set multiple=\"true\" to enable this option." % self.name )
        self.is_dynamic = True
        self._parse_options( input_source )
        # Load conversions required for the dataset input
        self.conversions = []
        for name, conv_extensions in input_source.parse_conversion_tuples():
            assert None not in [ name, conv_extensions ], 'A name (%s) and type (%s) are required for explicit conversion' % ( name, conv_extensions )
            conv_types = [ tool.app.datatypes_registry.get_datatype_by_extension( conv_extensions.lower() ) ]
            self.conversions.append( ( name, conv_extensions, conv_types ) )

    def match_collections( self, history, dataset_matcher, reduction=True ):
        dataset_collection_matcher = DatasetCollectionMatcher( dataset_matcher )

        for history_dataset_collection in history.active_dataset_collections:
            if dataset_collection_matcher.hdca_match( history_dataset_collection, reduction=reduction ):
                yield history_dataset_collection

    def match_datasets( self, history, dataset_matcher ):

        def dataset_collector( hdas, parent_hid ):
            for i, hda in enumerate( hdas ):
                if parent_hid is not None:
                    hid = "%s.%d" % ( parent_hid, i + 1 )
                else:
                    hid = str( hda.hid )
                hda_match = dataset_matcher.hda_match( hda )
                if not hda_match:
                    continue
                yield (hda_match, hid)
                # Also collect children via association object
                for item in dataset_collector( hda.children, hid ):
                    yield item

        for item in dataset_collector( history.active_datasets_children_and_roles, None ):
            yield item

    def from_json( self, value, trans, other_values={} ):
        if trans.workflow_building_mode is workflow_building_modes.ENABLED:
            return None
        if not value and not self.optional:
            raise ValueError( "Specify a dataset of the required format / build." )
        if value in [ None, "None", '' ]:
            return None
        if isinstance( value, dict ) and 'values' in value:
            value = self.to_python( value, trans.app )
        if isinstance( value, string_types ) and value.find( "," ) > 0:
            value = [ int( value_part ) for value_part in value.split( "," ) ]
        if isinstance( value, list ):
            rval = []
            found_hdca = False
            for single_value in value:
                if isinstance( single_value, dict ) and 'src' in single_value and 'id' in single_value:
                    if single_value['src'] == 'hda':
                        rval.append( trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( trans.security.decode_id(single_value['id']) ))
                    elif single_value['src'] == 'hdca':
                        found_hdca = True
                        decoded_id = trans.security.decode_id( single_value[ 'id' ] )
                        rval.append( trans.sa_session.query( trans.app.model.HistoryDatasetCollectionAssociation ).get( decoded_id ) )
                    else:
                        raise ValueError("Unknown input source %s passed to job submission API." % single_value['src'])
                elif isinstance( single_value, trans.app.model.HistoryDatasetCollectionAssociation ):
                    rval.append( single_value )
                elif isinstance( single_value, trans.app.model.HistoryDatasetAssociation ):
                    rval.append( single_value )
                else:
                    rval.append( trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( single_value ) )
            if found_hdca:
                for val in rval:
                    if not isinstance( val, trans.app.model.HistoryDatasetCollectionAssociation ):
                        raise ValueError( "If collections are supplied to multiple data input parameter, only collections may be used." )
        elif isinstance( value, trans.app.model.HistoryDatasetAssociation ):
            rval = value
        elif isinstance( value, dict ) and 'src' in value and 'id' in value:
            if value['src'] == 'hda':
                rval = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( trans.security.decode_id(value['id']) )
            elif value['src'] == 'hdca':
                decoded_id = trans.security.decode_id( value[ 'id' ] )
                rval = trans.sa_session.query( trans.app.model.HistoryDatasetCollectionAssociation ).get( decoded_id )
            else:
                raise ValueError("Unknown input source %s passed to job submission API." % value['src'])
        elif str( value ).startswith( "__collection_reduce__|" ):
            encoded_ids = [ v[ len( "__collection_reduce__|" ): ] for v in str( value ).split(",") ]
            decoded_ids = map( trans.security.decode_id, encoded_ids )
            rval = []
            for decoded_id in decoded_ids:
                hdca = trans.sa_session.query( trans.app.model.HistoryDatasetCollectionAssociation ).get( decoded_id )
                rval.append( hdca )
        elif isinstance( value, trans.app.model.HistoryDatasetCollectionAssociation ):
            rval = value
        else:
            rval = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( value )
        if isinstance( rval, list ):
            values = rval
        else:
            values = [ rval ]
        for v in values:
            if v:
                if v.deleted:
                    raise ValueError( "The previously selected dataset has been deleted." )
                if hasattr( v, "dataset" ) and v.dataset.state in [ galaxy.model.Dataset.states.ERROR, galaxy.model.Dataset.states.DISCARDED ]:
                    raise ValueError( "The previously selected dataset has entered an unusable state" )
        if not self.multiple:
            if len( values ) > 1:
                raise ValueError( "More than one dataset supplied to single input dataset parameter." )
            if len( values ) > 0:
                rval = values[ 0 ]
            else:
                raise ValueError( "Invalid dataset supplied to single input dataset parameter." )
        return rval

    def to_param_dict_string( self, value, other_values={} ):
        if value is None:
            return "None"
        return value.file_name

    def value_to_display_text( self, value, app ):
        if value and not isinstance( value, list ):
            value = [ value ]
        if value:
            try:
                return ", ".join( [ "%s: %s" % ( item.hid, item.name ) for item in value ] )
            except:
                pass
        return "No dataset."

    def validate( self, value, trans=None ):
        dataset_count = 0
        for validator in self.validators:
            def do_validate( v ):
                if validator.requires_dataset_metadata and v and hasattr( v, 'dataset' ) and v.dataset.state != galaxy.model.Dataset.states.OK:
                    return
                else:
                    validator.validate( v, trans )

            if value and self.multiple:
                if not isinstance( value, list ):
                    value = [ value ]
                for v in value:
                    if isinstance(v, galaxy.model.HistoryDatasetCollectionAssociation):
                        for dataset_instance in v.collection.dataset_instances:
                            dataset_count += 1
                            do_validate( dataset_instance )
                    else:
                        dataset_count += 1
                        do_validate( v )
            else:
                if value:
                    dataset_count += 1
                do_validate( value )

        if self.min is not None:
            if self.min > dataset_count:
                raise ValueError( "At least %d datasets are required." % self.min )
        if self.max is not None:
            if self.max < dataset_count:
                raise ValueError( "At most %d datasets are required." % self.max )

    def get_dependencies( self ):
        """
        Get the *names* of the other params this param depends on.
        """
        if self.options:
            return self.options.get_dependency_names()
        else:
            return []

    def converter_safe( self, other_values, trans ):
        if self.tool is None or self.tool.has_multiple_pages or not hasattr( trans, 'workflow_building_mode' ) or trans.workflow_building_mode:
            return False
        if other_values is None:
            return True  # we don't know other values, so we can't check, assume ok
        converter_safe = [True]

        def visitor( prefix, input, value, parent=None ):
            if isinstance( input, SelectToolParameter ) and self.name in input.get_dependencies():
                if input.is_dynamic and ( input.dynamic_options or ( not input.dynamic_options and not input.options ) or not input.options.converter_safe ):
                    converter_safe[0] = False  # This option does not allow for conversion, i.e. uses contents of dataset file to generate options
        self.tool.visit_inputs( other_values, visitor )
        return False not in converter_safe

    def get_options_filter_attribute( self, value ):
        # HACK to get around current hardcoded limitation of when a set of dynamic options is defined for a DataToolParameter
        # it always causes available datasets to be filtered by dbkey
        # this behavior needs to be entirely reworked (in a backwards compatible manner)
        options_filter_attribute = self.options_filter_attribute
        if options_filter_attribute is None:
            return value.get_dbkey()
        if options_filter_attribute.endswith( "()" ):
            call_attribute = True
            options_filter_attribute = options_filter_attribute[:-2]
        else:
            call_attribute = False
        ref = value
        for attribute in options_filter_attribute.split( '.' ):
            ref = getattr( ref, attribute )
        if call_attribute:
            ref = ref()
        return ref

    def to_dict( self, trans, other_values={} ):
        # create dictionary and fill default parameters
        d = super( DataToolParameter, self ).to_dict( trans )
        extensions = self.extensions
        datatypes_registery = self._datatypes_registery( trans, self.tool )
        all_edam_formats = datatypes_registery.edam_formats if hasattr( datatypes_registery, 'edam_formats' ) else {}
        all_edam_data = datatypes_registery.edam_data if hasattr( datatypes_registery, 'edam_formats' ) else {}
        edam_formats = [all_edam_formats.get(ext, None) for ext in extensions]
        edam_data = [all_edam_data.get(ext, None) for ext in extensions]

        d['extensions'] = extensions
        d['edam'] = {'edam_formats': edam_formats, 'edam_data': edam_data}
        d['multiple'] = self.multiple
        if self.multiple:
            # For consistency, should these just always be in the dict?
            d['min'] = self.min
            d['max'] = self.max
        d['options'] = {'hda': [], 'hdca': []}

        # return dictionary without options if context is unavailable
        history = trans.history
        if history is None or trans.workflow_building_mode is workflow_building_modes.ENABLED:
            return d

        # prepare dataset/collection matching
        dataset_matcher = DatasetMatcher( trans, self, None, other_values )
        multiple = self.multiple

        # build and append a new select option
        def append( list, id, hid, name, src, keep=False ):
            return list.append( { 'id' : trans.security.encode_id( id ), 'hid' : hid, 'name' : name, 'src' : src, 'keep': keep } )

        # add datasets
        visible_hda = other_values.get( self.name )
        has_matched = False
        for hda in history.active_datasets_children_and_roles:
            match = dataset_matcher.hda_match( hda, check_security=False )
            if match:
                m = match.hda
                has_matched = has_matched or visible_hda == m or visible_hda == hda
                m_name = '%s (as %s)' % ( match.original_hda.name, match.target_ext ) if match.implicit_conversion else m.name
                append( d[ 'options' ][ 'hda' ], m.id, m.hid, m_name if m.visible else '(hidden) %s' % m_name, 'hda' )
        if not has_matched and hasattr( visible_hda, 'id' ) and hasattr( visible_hda, 'hid' ) and hasattr( visible_hda, 'name' ):
            append( d[ 'options' ][ 'hda' ], visible_hda.id, visible_hda.hid, '(unavailable) %s' % visible_hda.name, 'hda', True )

        # add dataset collections
        dataset_collection_matcher = DatasetCollectionMatcher( dataset_matcher )
        for hdca in history.active_dataset_collections:
            if dataset_collection_matcher.hdca_match( hdca, reduction=multiple ):
                append( d[ 'options' ][ 'hdca' ], hdca.id, hdca.hid, hdca.name, 'hdca' )

        # sort both lists
        d['options']['hda'] = sorted(d['options']['hda'], key=lambda k: k['hid'], reverse=True)
        d['options']['hdca'] = sorted(d['options']['hdca'], key=lambda k: k['hid'], reverse=True)

        # return final dictionary
        return d


class DataCollectionToolParameter( BaseDataToolParameter ):
    """
    """

    def __init__( self, tool, input_source, trans=None ):
        input_source = ensure_input_source( input_source )
        super(DataCollectionToolParameter, self).__init__( tool, input_source, trans )
        self._parse_formats( trans, tool, input_source )
        collection_types = input_source.get("collection_type", None)
        if collection_types:
            collection_types = [t.strip() for t in collection_types.split(",")]
        self._collection_types = collection_types
        self.multiple = False  # Accessed on DataToolParameter a lot, may want in future
        self.is_dynamic = True
        self._parse_options( input_source )  # TODO: Review and test.

    @property
    def collection_types( self ):
        return self._collection_types

    def _history_query( self, trans ):
        dataset_collection_type_descriptions = trans.app.dataset_collections_service.collection_type_descriptions
        return history_query.HistoryQuery.from_parameter( self, dataset_collection_type_descriptions )

    def match_collections( self, trans, history, dataset_matcher ):
        dataset_collections = trans.app.dataset_collections_service.history_dataset_collections( history, self._history_query( trans ) )
        dataset_collection_matcher = DatasetCollectionMatcher( dataset_matcher )

        for dataset_collection_instance in dataset_collections:
            if not dataset_collection_matcher.hdca_match( dataset_collection_instance ):
                continue
            yield dataset_collection_instance

    def match_multirun_collections( self, trans, history, dataset_matcher ):
        dataset_collection_matcher = DatasetCollectionMatcher( dataset_matcher )

        for history_dataset_collection in history.active_dataset_collections:
            if not self._history_query( trans ).can_map_over( history_dataset_collection ):
                continue

            datasets_match = dataset_collection_matcher.hdca_match( history_dataset_collection )
            if datasets_match:
                yield history_dataset_collection

    def from_json( self, value, trans, other_values={} ):
        rval = None
        if trans.workflow_building_mode is workflow_building_modes.ENABLED:
            return None
        if not value and not self.optional:
            raise ValueError( "Specify a dataset collection of the correct type." )
        if value in [None, "None"]:
            return None
        if isinstance( value, dict ) and 'values' in value:
            value = self.to_python( value, trans.app )
        if isinstance( value, string_types ) and value.find( "," ) > 0:
            value = [ int( value_part ) for value_part in value.split( "," ) ]
        elif isinstance( value, trans.app.model.HistoryDatasetCollectionAssociation ):
            rval = value
        elif isinstance( value, trans.app.model.DatasetCollectionElement ):
            # When mapping over nested collection - this paramter will recieve
            # a DatasetCollectionElement instead of a
            # HistoryDatasetCollectionAssociation.
            rval = value
        elif isinstance( value, dict ) and 'src' in value and 'id' in value:
            if value['src'] == 'hdca':
                rval = trans.sa_session.query( trans.app.model.HistoryDatasetCollectionAssociation ).get( trans.security.decode_id(value['id']) )
        elif isinstance( value, list ):
            if len( value ) > 0:
                value = value[0]
                if isinstance( value, dict ) and 'src' in value and 'id' in value:
                    if value['src'] == 'hdca':
                        rval = trans.sa_session.query( trans.app.model.HistoryDatasetCollectionAssociation ).get( trans.security.decode_id(value['id']) )
        elif isinstance( value, string_types ):
            if value.startswith( "dce:" ):
                rval = trans.sa_session.query( trans.app.model.DatasetCollectionElement ).get( value[ len( "dce:"): ] )
            elif value.startswith( "hdca:" ):
                rval = trans.sa_session.query( trans.app.model.HistoryDatasetCollectionAssociation ).get( value[ len( "hdca:"): ] )
            else:
                rval = trans.sa_session.query( trans.app.model.HistoryDatasetCollectionAssociation ).get( value )
        if rval and isinstance( rval, trans.app.model.HistoryDatasetCollectionAssociation ):
            if rval.deleted:
                raise ValueError( "The previously selected dataset collection has been deleted" )
            # TODO: Handle error states, implement error states ...
        return rval

    def value_to_display_text( self, value, app ):
        try:
            if isinstance( value, galaxy.model.HistoryDatasetCollectionAssociation ):
                display_text = "%s: %s" % ( value.hid, value.name )
            else:
                display_text = "Element %d:%s" % ( value.identifier_index, value.identifier_name )
        except AttributeError:
            display_text = "No dataset collection."
        return display_text

    def validate( self, value, trans=None ):
        return True  # TODO

    def to_dict( self, trans, other_values=None ):
        # create dictionary and fill default parameters
        other_values = other_values or {}
        d = super( DataCollectionToolParameter, self ).to_dict( trans )
        d['extensions'] = self.extensions
        d['multiple'] = self.multiple
        d['options'] = {'hda': [], 'hdca': []}

        # return dictionary without options if context is unavailable
        history = trans.history
        if history is None or trans.workflow_building_mode is workflow_building_modes.ENABLED:
            return d

        # prepare dataset/collection matching
        dataset_matcher = DatasetMatcher( trans, self, None, other_values )

        # append directly matched collections
        for hdca in self.match_collections( trans, history, dataset_matcher ):
            d['options']['hdca'].append({
                'id': trans.security.encode_id( hdca.id ),
                'hid': hdca.hid,
                'name': hdca.name,
                'src': 'hdca'
            })

        # append matching subcollections
        for hdca in self.match_multirun_collections( trans, history, dataset_matcher ):
            subcollection_type = self._history_query( trans ).can_map_over( hdca ).collection_type
            d['options']['hdca'].append({
                'id': trans.security.encode_id( hdca.id ),
                'hid': hdca.hid,
                'name': hdca.name,
                'src': 'hdca',
                'map_over_type': subcollection_type
            })

        # sort both lists
        d['options']['hdca'] = sorted(d['options']['hdca'], key=lambda k: k['hid'], reverse=True)

        # return final dictionary
        return d


class HiddenDataToolParameter( HiddenToolParameter, DataToolParameter ):
    """
    Hidden parameter that behaves as a DataToolParameter. As with all hidden
    parameters, this is a HACK.
    """
    def __init__( self, tool, elem ):
        DataToolParameter.__init__( self, tool, elem )
        self.value = "None"
        self.type = "hidden_data"
        self.hidden = True

    def get_initial_value( self, trans, other_values ):
        return None


class LibraryDatasetToolParameter( ToolParameter ):
    """
    Parameter that lets users select a LDDA from a modal window, then use it within the wrapper.
    """

    def __init__( self, tool, input_source, context=None ):
        input_source = ensure_input_source( input_source )
        ToolParameter.__init__( self, tool, input_source )
        self.multiple = input_source.get_bool( 'multiple', True )

    def get_initial_value( self, trans, other_values ):
        return None

    def from_json( self, value, trans, other_values={} ):
        return self.to_python( value, trans.app, other_values=other_values, validate=True )

    def to_param_dict_string( self, value, other_values={} ):
        if value is None:
            return 'None'
        elif self.multiple:
            return [ dataset.get_file_name() for dataset in value ]
        else:
            return value[ 0 ].get_file_name()

    # converts values to json representation:
    #   { id: LibraryDatasetDatasetAssociation.id, name: LibraryDatasetDatasetAssociation.name, src: 'lda' }
    def to_json( self, value, app, use_security ):
        if not isinstance( value, list ):
            value = [value]
        lst = []
        for item in value:
            lda_id = lda_name = None
            if isinstance(item, app.model.LibraryDatasetDatasetAssociation):
                lda_id = app.security.encode_id( item.id ) if use_security else item.id
                lda_name = item.name
            elif isinstance(item, dict):
                lda_id = item.get('id')
                lda_name = item.get('name')
            else:
                lst = []
                break
            if lda_id is not None:
                lst.append( {
                    'id'   : lda_id,
                    'name' : lda_name,
                    'src'  : 'ldda'
                } )
        if len( lst ) == 0:
            return None
        else:
            return lst

    # converts values into python representation:
    #   LibraryDatasetDatasetAssociation
    # valid input values (incl. arrays of mixed sets) are:
    #   1. LibraryDatasetDatasetAssociation
    #   2. LibraryDatasetDatasetAssociation.id
    #   3. { id: LibraryDatasetDatasetAssociation.id, ... }
    def to_python( self, value, app, other_values={}, validate=False ):
        if not isinstance( value, list ):
            value = [value]
        lst = []
        for item in value:
            if isinstance(item, app.model.LibraryDatasetDatasetAssociation):
                lst.append(item)
            else:
                lda_id = None
                if isinstance(item, dict):
                    lda_id = item.get('id')
                elif isinstance(item, string_types):
                    lda_id = item
                else:
                    lst = []
                    break
                lda = app.model.context.query( app.model.LibraryDatasetDatasetAssociation ).get( lda_id if isinstance( lda_id, int ) else app.security.decode_id( lda_id ) )
                if lda is not None:
                    lst.append( lda )
                elif validate:
                    raise ValueError( "One of the selected library datasets is invalid or not available anymore." )
        if len( lst ) == 0:
            if not self.optional and validate:
                raise ValueError( "Please select a valid library dataset." )
            return None
        else:
            return lst

    def to_dict( self, trans, other_values=None ):
        d = super( LibraryDatasetToolParameter, self ).to_dict( trans )
        d['multiple'] = self.multiple
        return d


parameter_types = dict(
    text=TextToolParameter,
    integer=IntegerToolParameter,
    float=FloatToolParameter,
    boolean=BooleanToolParameter,
    genomebuild=GenomeBuildParameter,
    select=SelectToolParameter,
    color=ColorToolParameter,
    data_column=ColumnListParameter,
    hidden=HiddenToolParameter,
    hidden_data=HiddenDataToolParameter,
    baseurl=BaseURLToolParameter,
    file=FileToolParameter,
    ftpfile=FTPFileToolParameter,
    data=DataToolParameter,
    data_collection=DataCollectionToolParameter,
    library_data=LibraryDatasetToolParameter,
    drill_down=DrillDownSelectToolParameter
)


class RuntimeValue( object ):
    """
    Wrapper to note a value that is not yet set, but will be required at runtime.
    """
    pass
