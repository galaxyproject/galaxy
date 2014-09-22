"""
Basic tool parameters.
"""

import logging
import string
import sys
import os
import os.path
import urllib
from elementtree.ElementTree import XML, Element
from galaxy import config, datatypes, util
from galaxy.web import form_builder
from galaxy.util.bunch import Bunch
from galaxy.util import string_as_bool, sanitize_param, unicodify
from galaxy.util import listify
from galaxy.util.odict import odict
from sanitize import ToolParameterSanitizer
import validation
import dynamic_options
from ..parameters import history_query
from .dataset_matcher import DatasetMatcher
from .dataset_matcher import DatasetCollectionMatcher
# For BaseURLToolParameter
from galaxy.web import url_for
from galaxy.model.item_attrs import Dictifiable
import galaxy.model

log = logging.getLogger(__name__)


class ToolParameter( object, Dictifiable ):
    """
    Describes a parameter accepted by a tool. This is just a simple stub at the
    moment but in the future should encapsulate more complex parameters (lists
    of valid choices, validation logic, ...)
    """
    dict_collection_visible_keys = ( 'name', 'type', 'label', 'help' )

    def __init__( self, tool, param, context=None ):
        self.tool = tool
        self.refresh_on_change = False
        self.refresh_on_change_values = []
        self.name = param.get("name")
        self.type = param.get("type")
        self.label = util.xml_text(param, "label")
        self.help = util.xml_text(param, "help")
        self.sanitizer = param.find( "sanitizer" )
        if self.sanitizer is not None:
            self.sanitizer = ToolParameterSanitizer.from_element( self.sanitizer )
        self.html = "no html set"
        self.repeat = param.get("repeat", None)
        self.condition = param.get( "condition", None )
        # Optional DataToolParameters are used in tools like GMAJ and LAJ
        self.optional = string_as_bool( param.get( 'optional', False ) )
        self.validators = []
        for elem in param.findall("validator"):
            self.validators.append( validation.Validator.from_element( self, elem ) )

    @property
    def visible( self ):
        """Return true if the parameter should be rendered on the form"""
        return True

    def get_label( self ):
        """Return user friendly name for the parameter"""
        if self.label:
            return self.label
        else:
            return self.name

    def get_html_field( self, trans=None, value=None, other_values={} ):
        raise TypeError( "Abstract Method" )

    def get_html( self, trans=None, value=None, other_values={}):
        """
        Returns the html widget corresponding to the parameter.
        Optionally attempt to retain the current value specific by 'value'
        """
        return self.get_html_field( trans, value, other_values ).get_html()

    def from_html( self, value, trans=None, other_values={} ):
        """
        Convert a value from an HTML POST into the parameters preferred value
        format.
        """
        return value

    def from_json( self, value, trans=None, other_values={} ):
        return self.from_html( value, trans, other_values )

    def get_initial_value( self, trans, context, history=None ):
        """
        Return the starting value of the parameter
        """
        return None

    def get_initial_value_from_history_prevent_repeats( self, trans, context, already_used, history=None ):
        """
        Get the starting value for the parameter, but if fetching from the history, try
        to find a value that has not yet been used. already_used is a list of objects that
        tools must manipulate (by adding to it) to store a memento that they can use to detect
        if a value has already been chosen from the history. This is to support the capability to
        choose each dataset once
        """
        return self.get_initial_value(trans, context, history=history)

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

    def to_html_value( self, value, app ):
        """Convert an object value to the value expected from an html post"""
        return self.to_string( value, app )

    def to_string( self, value, app ):
        """Convert a value to a string representation suitable for persisting"""
        if not isinstance( value, basestring ):
            value = str( value )
        return unicodify( value )

    def to_python( self, value, app ):
        """Convert a value created with to_string back to an object representation"""
        return value

    def value_to_basic( self, value, app ):
        if isinstance( value, RuntimeValue ):
            return { "__class__": "RuntimeValue" }
        return self.to_string( value, app )

    def value_from_basic( self, value, app, ignore_errors=False ):
        # HACK: Some things don't deal with unicode well, psycopg problem?
        if type( value ) == unicode:
            value = str( value )
        # Handle Runtime values (valid for any parameter?)
        if isinstance( value, dict ) and '__class__' in value and value['__class__'] == "RuntimeValue":
            return RuntimeValue()
        # Delegate to the 'to_python' method
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
        return unicodify( value )

    def to_param_dict_string( self, value, other_values={} ):
        """Called via __str__ when used in the Cheetah template"""
        if value is None:
            value = ""
        elif not isinstance( value, basestring ):
            value = str( value )
        if self.tool is None or self.tool.options.sanitize:
            if self.sanitizer:
                value = self.sanitizer.sanitize_param( value )
            else:
                value = sanitize_param( value )
        return value

    def validate( self, value, history=None ):
        if value == "" and self.optional:
            return
        for validator in self.validators:
            validator.validate( value, history )

    def need_late_validation( self, trans, context ):
        return False

    def to_dict( self, trans, view='collection', value_mapper=None ):
        """ to_dict tool parameter. This can be overridden by subclasses. """
        tool_dict = super( ToolParameter, self ).to_dict()
        #TODO: wrapping html as it causes a lot of errors on subclasses - needs histories, etc.
        try:
            tool_dict[ 'html' ] = urllib.quote( self.get_html( trans ) )
        except AssertionError, e:
            pass #HACK for assert trans.history, 'requires a history'

        tool_dict[ 'model_class' ] = self.__class__.__name__
        if hasattr( self, 'value' ):
            tool_dict[ 'value' ] = self.value
        return tool_dict

    @classmethod
    def build( cls, tool, param ):
        """Factory method to create parameter of correct type"""
        param_name = param.get( "name" )
        if not param_name:
            raise ValueError( "Tool parameter '%s' requires a 'name'" % (param_name ) )
        param_type = param.get("type")
        if not param_type:
            raise ValueError( "Tool parameter '%s' requires a 'type'" % ( param_name ) )
        elif param_type not in parameter_types:
            raise ValueError( "Tool parameter '%s' uses an unknown type '%s'" % ( param_name, param_type ) )
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
        self.size = elem.get( 'size' )
        self.value = elem.get( 'value' )
        self.area = string_as_bool( elem.get( 'area', False ) )

    def get_html_field( self, trans=None, value=None, other_values={} ):
        if value is None:
            value = self.value
        if self.area:
            return form_builder.TextArea( self.name, self.size, value )
        else:
            return form_builder.TextField( self.name, self.size, value )

    def get_initial_value( self, trans, context, history=None ):
        return self.value

    def to_dict( self, trans, view='collection', value_mapper=None ):
        d = super(TextToolParameter, self).to_dict(trans)
        d['area'] = self.area
        return d

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

    dict_collection_visible_keys = ToolParameter.dict_collection_visible_keys + ( 'min', 'max' )

    def __init__( self, tool, elem ):
        TextToolParameter.__init__( self, tool, elem )
        if self.value:
            try:
                int( self.value )
            except:
                raise ValueError( "An integer is required" )
        elif self.value is None and not self.optional:
            raise ValueError( "The settings for the field named '%s' require a 'value' setting and optionally a default value which must be an integer" % self.name )
        self.min = elem.get( 'min' )
        self.max = elem.get( 'max' )
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

    def get_html_field( self, trans=None, value=None, other_values={} ):
        if isinstance( value, int ):
            value = str( value )
        return super( IntegerToolParameter, self ).get_html_field( trans=trans, value=value, other_values=other_values )

    def from_html( self, value, trans=None, other_values={} ):
        try:
            return int( value )
        except:
            if not value and self.optional:
                return ""
            raise ValueError( "An integer is required" )

    def to_string( self, value, app ):
        """Convert a value to a string representation suitable for persisting"""
        if value is None:
            return ""
        else:
            return str( value )

    def to_python( self, value, app ):
        try:
            return int( value )
        except Exception, err:
            if not value and self.optional:
                return None
            raise err

    def get_initial_value( self, trans, context, history=None ):
        if self.value:
            return int( self.value )
        else:
            return None


class FloatToolParameter( TextToolParameter ):
    """
    Parameter that takes a real number value.

    >>> p = FloatToolParameter( None, XML( '<param name="blah" type="float" size="4" value="3.141592" />' ) )
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

    dict_collection_visible_keys = ToolParameter.dict_collection_visible_keys + ( 'min', 'max' )

    def __init__( self, tool, elem ):
        TextToolParameter.__init__( self, tool, elem )
        self.min = elem.get( 'min' )
        self.max = elem.get( 'max' )
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

    def get_html_field( self, trans=None, value=None, other_values={} ):
        if isinstance( value, float ):
            value = str( value )
        return super( FloatToolParameter, self ).get_html_field( trans=trans, value=value, other_values=other_values )

    def from_html( self, value, trans=None, other_values={} ):
        try:
            return float( value )
        except:
            if not value and self.optional:
                return ""
            raise ValueError( "A real number is required" )

    def to_string( self, value, app ):
        """Convert a value to a string representation suitable for persisting"""
        if value is None:
            return ""
        else:
            return str( value )

    def to_python( self, value, app ):
        try:
            return float( value )
        except Exception, err:
            if not value and self.optional:
                return None
            raise err

    def get_initial_value( self, trans, context, history=None ):
        try:
            return float( self.value )
        except:
            return None


class BooleanToolParameter( ToolParameter ):
    """
    Parameter that takes one of two values.

    >>> p = BooleanToolParameter( None, XML( '<param name="blah" type="boolean" checked="yes" truevalue="bulletproof vests" falsevalue="cellophane chests" />' ) )
    >>> print p.name
    blah
    >>> print p.get_html()
    <input type="checkbox" id="blah" name="blah" value="true" checked="checked"><input type="hidden" name="blah" value="true">
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
        self.checked = string_as_bool( elem.get( 'checked' ) )

    def get_html_field( self, trans=None, value=None, other_values={} ):
        checked = self.checked
        if value is not None:
            checked = form_builder.CheckboxField.is_checked( value )
        return form_builder.CheckboxField( self.name, checked, refresh_on_change=self.refresh_on_change )

    def from_html( self, value, trans=None, other_values={} ):
        return form_builder.CheckboxField.is_checked( value )

    def from_json( self, value, trans=None, other_values={} ):
        return string_as_bool( value )

    def to_html_value( self, value, app ):
        if value:
            return [ 'true', 'true' ]
        else:
            return [ 'true' ]

    def to_python( self, value, app ):
        return ( value == 'True' )

    def get_initial_value( self, trans, context, history=None ):
        return self.checked

    def to_param_dict_string( self, value, other_values={} ):
        if value:
            return self.truevalue
        else:
            return self.falsevalue

    def to_dict( self, trans, view='collection', value_mapper=None ):
        d = super(BooleanToolParameter, self).to_dict(trans)
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

    >>> p = FileToolParameter( None, XML( '<param name="blah" type="file"/>' ) )
    >>> print p.name
    blah
    >>> print p.get_html()
    <input type="file" name="blah">
    >>> p = FileToolParameter( None, XML( '<param name="blah" type="file" ajax-upload="true"/>' ) )
    >>> print p.get_html()
    <input type="file" name="blah" galaxy-ajax-upload="true">
    """
    def __init__( self, tool, elem ):
        """
        Example: C{<param name="bins" type="file" />}
        """
        ToolParameter.__init__( self, tool, elem )
        self.ajax = string_as_bool( elem.get( 'ajax-upload' ) )

    def get_html_field( self, trans=None, value=None, other_values={}  ):
        return form_builder.FileField( self.name, ajax=self.ajax, value=value )

    def from_html( self, value, trans=None, other_values={} ):
        # Middleware or proxies may encode files in special ways (TODO: this
        # should be pluggable)
        if type( value ) == dict:
            upload_store = self.tool.app.config.nginx_upload_store
            assert upload_store, \
                "Request appears to have been processed by nginx_upload_module \
                but Galaxy is not configured to recognize it"
            # Check that the file is in the right location
            local_filename = os.path.abspath( value['path'] )
            assert local_filename.startswith( upload_store ), \
                "Filename provided by nginx (%s) is not in correct directory (%s)" % (local_filename, upload_store)
            value = dict(
                filename=value["name"],
                local_filename=local_filename
            )
        return value

    def get_required_enctype( self ):
        """
        File upload elements require the multipart/form-data encoding
        """
        return "multipart/form-data"

    def to_string( self, value, app ):
        if value in [ None, '' ]:
            return None
        elif isinstance( value, unicode ) or isinstance( value, str ):
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
        elif isinstance( value, unicode ) or isinstance( value, str ):
            return value
        else:
            raise Exception( "FileToolParameter cannot be persisted" )

    def get_initial_value( self, trans, context, history=None ):
        return None


class FTPFileToolParameter( ToolParameter ):
    """
    Parameter that takes a file uploaded via FTP as a value.
    """
    def __init__( self, tool, elem ):
        """
        Example: C{<param name="bins" type="file" />}
        """
        ToolParameter.__init__( self, tool, elem )

    @property
    def visible( self ):
        if self.tool.app.config.ftp_upload_dir is None or self.tool.app.config.ftp_upload_site is None:
            return False
        return True

    def get_html_field( self, trans=None, value=None, other_values={}  ):
        if trans is None or trans.user is None:
            user_ftp_dir = None
        else:
            user_ftp_dir = trans.user_ftp_dir
        return form_builder.FTPFileField( self.name, user_ftp_dir, trans.app.config.ftp_upload_site, value=value )

    def from_html( self, value, trans=None, other_values={} ):
        try:
            assert type( value ) is list
        except:
            value = [ value ]
        return value

    def to_string( self, value, app ):
        if value in [ None, '' ]:
            return None
        elif isinstance( value, unicode ) or isinstance( value, str ) or isinstance( value, list ):
            return value

    def to_python( self, value, app ):
        if value is None:
            return None
        elif isinstance( value, unicode ) or isinstance( value, str ) or isinstance( value, list ):
            return value

    def get_initial_value( self, trans, context, history=None ):
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
        self.value = elem.get( 'value' )

    def get_html_field( self, trans=None, value=None, other_values={} ):
        return form_builder.HiddenField( self.name, self.value )

    def get_initial_value( self, trans, context, history=None ):
        return self.value

    def get_label( self ):
        return None

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
        self.value = elem.get( 'value', '' )

    def get_value( self, trans ):
        # url = trans.request.base + self.value
        url = url_for( self.value, qualified=True )
        return url

    def get_html_field( self, trans=None, value=None, other_values={} ):
        return form_builder.HiddenField( self.name, self.get_value( trans ) )

    def get_initial_value( self, trans, context, history=None ):
        return self.value

    def get_label( self ):
        # BaseURLToolParameters are ultimately "hidden" parameters
        return None


DEFAULT_VALUE_MAP = lambda x: x


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
    <select name="blah" last_selected_value="y">
    <option value="x">I am X</option>
    <option value="y" selected>I am Y</option>
    <option value="z">I am Z</option>
    </select>
    >>> print p.get_html( value="z" )
    <select name="blah" last_selected_value="z">
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
    <select name="blah" multiple last_selected_value="z">
    <option value="x">I am X</option>
    <option value="y" selected>I am Y</option>
    <option value="z" selected>I am Z</option>
    </select>
    >>> print p.get_html( value=["x","y"])
    <select name="blah" multiple last_selected_value="y">
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
    <div class="checkUncheckAllPlaceholder" checkbox_name="blah"></div>
    <div><input type="checkbox" name="blah" value="x" id="blah|x"><label class="inline" for="blah|x">I am X</label></div>
    <div class="odd_row"><input type="checkbox" name="blah" value="y" id="blah|y" checked='checked'><label class="inline" for="blah|y">I am Y</label></div>
    <div><input type="checkbox" name="blah" value="z" id="blah|z" checked='checked'><label class="inline" for="blah|z">I am Z</label></div>
    >>> print p.get_html( value=["x","y"])
    <div class="checkUncheckAllPlaceholder" checkbox_name="blah"></div>
    <div><input type="checkbox" name="blah" value="x" id="blah|x" checked='checked'><label class="inline" for="blah|x">I am X</label></div>
    <div class="odd_row"><input type="checkbox" name="blah" value="y" id="blah|y" checked='checked'><label class="inline" for="blah|y">I am Y</label></div>
    <div><input type="checkbox" name="blah" value="z" id="blah|z"><label class="inline" for="blah|z">I am Z</label></div>
    >>> print p.to_param_dict_string( ["y", "z"] )
    y,z
    """
    def __init__( self, tool, elem, context=None ):
        ToolParameter.__init__( self, tool, elem )
        self.multiple = string_as_bool( elem.get( 'multiple', False ) )
        # Multiple selects are optional by default, single selection is the inverse.
        self.optional = string_as_bool( elem.get( 'optional', self.multiple ) )
        self.display = elem.get( 'display', None )
        self.separator = elem.get( 'separator', ',' )
        self.legal_values = set()
        # TODO: the <dynamic_options> tag is deprecated and should be replaced with the <options> tag.
        self.dynamic_options = elem.get( "dynamic_options", None )
        options = elem.find( 'options' )
        if options is None:
            self.options = None
        else:
            self.options = dynamic_options.DynamicOptions( options, self )
            for validator in self.options.validators:
                self.validators.append( validator )
        if self.dynamic_options is None and self.options is None:
            self.static_options = list()
            for index, option in enumerate( elem.findall( "option" ) ):
                value = option.get( "value" )
                self.legal_values.add( value )
                selected = string_as_bool( option.get( "selected", False ) )
                self.static_options.append( ( option.text or value, value, selected ) )
        self.is_dynamic = ( ( self.dynamic_options is not None ) or ( self.options is not None ) )

    def get_options( self, trans, other_values ):
        if self.options:
            return self.options.get_options( trans, other_values )
        elif self.dynamic_options:
            return eval( self.dynamic_options, self.tool.code_namespace, other_values )
        else:
            return self.static_options

    def get_legal_values( self, trans, other_values ):
        def _get_UnvalidatedValue_value( value ):
            if isinstance( value, UnvalidatedValue ):
                return value.value
            return value
        if self.options:
            return map( _get_UnvalidatedValue_value, set( v for _, v, _ in self.options.get_options( trans, other_values ) ) )
        elif self.dynamic_options:
            return set( v for _, v, _ in eval( self.dynamic_options, self.tool.code_namespace, other_values ) )
        else:
            return self.legal_values

    def get_html_field( self, trans=None, value=None, context={} ):
        # Dynamic options are not yet supported in workflow, allow
        # specifying the value as text for now.
        if self.need_late_validation( trans, context ):
            if value is not None:
                assert isinstance( value, UnvalidatedValue ), "Late validation needed for '%s', but provided value (%s) is not of type UnvalidatedValue (%s)." % ( self.name, value, type( value ) )
                value = value.value
            if self.multiple:
                if value is None:
                    value = ""
                else:
                    value = "\n".join( value )
                return form_builder.TextArea( self.name, value=value )
            else:
                return form_builder.TextField( self.name, value=(value or "") )
        if value is not None:
            if not isinstance( value, list ):
                value = [ value ]
            # We could have an unvalidated value here when e.g. running a workflow.
            value = [ val.value if isinstance( val, UnvalidatedValue ) else val for val in value ]
        field = form_builder.SelectField( self.name, self.multiple, self.display, self.refresh_on_change, refresh_on_change_values=self.refresh_on_change_values )
        options = self.get_options( trans, context )
        for text, optval, selected in options:
            if isinstance( optval, UnvalidatedValue ):
                optval = optval.value
                text = "%s (unvalidated)" % text
            if value:
                selected = ( optval in value )
            field.add_option( text, optval, selected )
        return field

    def from_html( self, value, trans=None, context={} ):
        if self.need_late_validation( trans, context ):
            if self.multiple:
                # While it is generally allowed that a select value can be '',
                # we do not allow this to be the case in a dynamically
                # generated multiple select list being set in workflow building
                # mode we instead treat '' as 'No option Selected' (None)
                if value == '':
                    value = None
                else:
                    if not isinstance( value, list ):
                        # Split on all whitespace. This not only provides flexibility
                        # in interpreting values but also is needed because many browsers
                        # use \r\n to separate lines.
                        value = value.split()
            return UnvalidatedValue( value )
        legal_values = self.get_legal_values( trans, context )
        if isinstance( value, list ):
            if not(self.repeat):
                assert self.multiple, "Multiple values provided but parameter is not expecting multiple values"
            rval = []
            for v in value:
                if v not in legal_values:
                    raise ValueError( "An invalid option was selected, please verify" )
                rval.append( v )
            return rval
        else:
            value_is_none = ( value == "None" and "None" not in legal_values )
            if value_is_none:
                if self.multiple:
                    if self.optional:
                        return []
                    else:
                        raise ValueError( "No option was selected but input is not optional." )
            if value not in legal_values:
                raise ValueError( "An invalid option was selected, please verify" )
            return value

    def to_html_value( self, value, app ):
        if isinstance( value, list ):
            return value
        else:
            return str( value )

    def to_param_dict_string( self, value, other_values={}, value_map=DEFAULT_VALUE_MAP ):
        if value is None:
            return "None"
        if isinstance( value, list ):
            if not( self.repeat ):
                assert self.multiple, "Multiple values provided but parameter is not expecting multiple values"
            value = map( str, value )
        else:
            value = str( value )
        if self.tool is None or self.tool.options.sanitize:
            if self.sanitizer:
                value = self.sanitizer.sanitize_param( value )
            else:
                value = sanitize_param( value )
        if isinstance( value, list ):
            value = self.separator.join( map( value_map, value ) )
        else:
            value = value_map( value )
        return value

    def value_to_basic( self, value, app ):
        if isinstance( value, UnvalidatedValue ):
            return { "__class__": "UnvalidatedValue", "value": value.value }
        elif isinstance( value, RuntimeValue ):
            # Need to handle runtime value's ourself since delegating to the
            # parent method causes the value to be turned into a string, which
            # breaks multiple selection
            return { "__class__": "RuntimeValue" }
        return value

    def value_from_basic( self, value, app, ignore_errors=False ):
        if isinstance( value, dict ) and value.get( "__class__", None ) == "UnvalidatedValue":
            return UnvalidatedValue( value["value"] )
        return super( SelectToolParameter, self ).value_from_basic( value, app, ignore_errors=ignore_errors )

    def need_late_validation( self, trans, context ):
        """
        Determine whether we need to wait to validate this parameters value
        given the current state. For parameters with static options this is
        always false (can always validate immediately). For parameters with
        dynamic options, we need to check whether the other parameters which
        determine what options are valid have been set. For the old style
        dynamic options which do not specify dependencies, this is always true
        (must validate at runtime).
        """
        # Option list is statically defined, never need late validation
        if not self.is_dynamic:
            return False
        # Old style dynamic options, no dependency information so there isn't
        # a lot we can do: if we're dealing with workflows, have to assume
        # late validation no matter what.
        if self.dynamic_options is not None and ( trans is None or trans.workflow_building_mode ):
            return True
        # If we got this far, we can actually look at the dependencies
        # to see if their values will not be available until runtime.
        for dep_name in self.get_dependencies():
            # This may not be completely correct, but it's possible to go
            # through the layers indicated below without assigning dep_value,
            # which is even worse.  TODO fix it?
            dep_value = None
            if dep_name in context:
                dep_value = context[ dep_name ]
            else:
                # Quick hack to check deeper in the context.
                # TODO: Context should really be scoped and the correct subset passed along.
                # This happens specifically in all the GATK tools, the way the reference genome is handled.
                for layer in context.itervalues():
                    if isinstance( layer, dict ) and self.name in layer and dep_name in layer:
                        dep_value = layer[dep_name]
            # Dependency on a dataset that does not yet exist
            if isinstance( dep_value, DummyDataset ):
                return True
            # Dependency on a value that has not been checked
            if isinstance( dep_value, UnvalidatedValue ):
                return True
            # Dependency on a value that does not yet exist
            if isinstance( dep_value, RuntimeValue ):
                return True
            #dataset not ready yet
            if hasattr( self, 'ref_input' ) and isinstance( dep_value, self.tool.app.model.HistoryDatasetAssociation ) and ( dep_value.is_pending or not dep_value.datatype.matches_any( self.ref_input.formats ) ):
                return True
        # Dynamic, but all dependenceis are known and have values
        return False

    def get_initial_value( self, trans, context, history=None ):
        # More working around dynamic options for workflow
        if self.need_late_validation( trans, context ):
            # Really the best we can do?
            return UnvalidatedValue( None )
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

    def value_to_display_text( self, value, app ):
        if isinstance( value, UnvalidatedValue ):
            suffix = "\n(value not yet validated)"
            value = value.value
        else:
            suffix = ""
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
        return "\n".join( rval ) + suffix

    def get_dependencies( self ):
        """
        Get the *names* of the other params this param depends on.
        """
        if self.options:
            return self.options.get_dependency_names()
        else:
            return []

    def to_dict( self, trans, view='collection', value_mapper=None ):
        d = super( SelectToolParameter, self ).to_dict( trans )

        # Get options, value.
        options = []
        try:
            options = self.get_options( trans, {} )
        except AssertionError:
            # we dont/cant set other_values (the {} above), so params that require other params to be filled will error:
            #       required dependency in filter_options
            #       associated DataToolParam in get_column_list
            pass

        d[ 'options' ] = options
        if options:
            value = options[0][1]
            for option in options:
                if option[2]:
                    # Found selected option.
                    value = option[1]
            d[ 'value' ] = value
            
        d['display'] = self.display
        d['multiple'] = self.multiple

        return d


class GenomeBuildParameter( SelectToolParameter ):
    """
    Select list that sets the last used genome build for the current history
    as "selected".

    >>> # Create a mock transaction with 'hg17' as the current build
    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch( history=Bunch( genome_build='hg17' ), db_builds=util.read_dbnames( None ) )

    >>> p = GenomeBuildParameter( None, XML(
    ... '''
    ... <param name="blah" type="genomebuild" />
    ... ''' ) )
    >>> print p.name
    blah

    >>> # hg17 should be selected by default
    >>> print p.get_html( trans ) # doctest: +ELLIPSIS
    <select name="blah" last_selected_value="hg17">
    <option value="?">unspecified (?)</option>
    ...
    <option value="hg18">Human Mar. 2006 (NCBI36/hg18) (hg18)</option>
    <option value="hg17" selected>Human May 2004 (NCBI35/hg17) (hg17)</option>
    ...
    </select>

    >>> # If the user selected something else already, that should be used
    >>> # instead
    >>> print p.get_html( trans, value='hg18' ) # doctest: +ELLIPSIS
    <select name="blah" last_selected_value="hg18">
    <option value="?">unspecified (?)</option>
    ...
    <option value="hg18" selected>Human Mar. 2006 (NCBI36/hg18) (hg18)</option>
    <option value="hg17">Human May 2004 (NCBI35/hg17) (hg17)</option>
    ...
    </select>

    >>> print p.filter_value( "hg17" )
    hg17
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

    def to_dict( self, trans, view='collection', value_mapper=None ):
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
            'options': options,
            'value': value
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
    def __init__( self, tool, elem ):
        SelectToolParameter.__init__( self, tool, elem )
        self.tool = tool
        self.numerical = string_as_bool( elem.get( "numerical", False ))
        self.force_select = string_as_bool( elem.get( "force_select", True ))
        self.accept_default = string_as_bool( elem.get( "accept_default", False ))
        self.data_ref = elem.get( "data_ref", None )
        self.ref_input = None
        # Legacy style default value specification...
        self.default_value = elem.get( "default_value", None )
        if self.default_value is None:
            # Newer style... more in line with other parameters.
            self.default_value = elem.get( "value", None )
        if self.default_value is not None:
            self.default_value = ColumnListParameter._strip_c( self.default_value )
        self.is_dynamic = True
        self.usecolnames = string_as_bool( elem.get( "use_header_names", False ))

    def from_html( self, value, trans=None, context={} ):
        """
        Label convention prepends column number with a 'c', but tool uses the integer. This
        removes the 'c' when entered into a workflow.
        """
        if self.multiple:
            #split on newline and ,
            if value:
                column_list = []
                if not isinstance( value, list ):
                    value = value.split( '\n' )
                for column in value:
                    for column2 in str( column ).split( ',' ):
                        column2 = column2.strip()
                        if column2:
                            column_list.append( column2 )
                value = map( ColumnListParameter._strip_c, column_list )
            else:
                value = []
        else:
            if value:
                value = ColumnListParameter._strip_c( value )
            else:
                value = None
        return super( ColumnListParameter, self ).from_html( value, trans, context )

    @staticmethod
    def _strip_c(column):
        if column.startswith( 'c' ):
            column = column.strip().lower()[1:]
        return column

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
                column_list.append( self.default_value or '1' )
            return column_list
        if not self.force_select:
            column_list.append( 'None' )
        if self.numerical:
            # If numerical was requested, filter columns based on metadata
            for i, col in enumerate( dataset.metadata.column_types ):
                if col == 'int' or col == 'float':
                    column_list.append( str( i + 1 ) )
        else:
            for i in range(0, dataset.metadata.columns):
                column_list.append( str( i + 1 ) )
        return column_list

    def get_options( self, trans, other_values ):
        """ show column labels rather than c1..cn if use_header_names=True
        """
        options = []
        colnames = None
        if self.usecolnames: # read first row - assume is a header with metadata useful for making good choices
            dataset = other_values[ self.data_ref ]
            try:
                head = open(dataset.get_file_name(),'r').readline()
                cnames = head.rstrip().split('\t')
                column_list = [('%d' % (i+1),'c%d: %s' % (i+1,x)) for i,x in enumerate(cnames)]
                if self.numerical: # If numerical was requested, filter columns based on metadata
                    if len(dataset.metadata.column_types) >= len(cnames):
                        numerics = [i for i,x in enumerate(dataset.metadata.column_types) if x == 'int' or x == 'float']
                        column_list = [column_list[i] for i in numerics]
            except:
                column_list = self.get_column_list( trans, other_values )
        else:
           column_list = self.get_column_list( trans, other_values )
        if len( column_list ) > 0 and not self.force_select:
            options.append( ('?', 'None', False) )
        for col in column_list:
            if col != 'None':
                if type(col) == type(()) and len(col) == 2: # fiddled
                    options.append((col[1],col[0],False))
                else:
                    options.append( ( 'c' + col, col, False ) )
        return options

    def get_initial_value( self, trans, context, history=None ):
        if self.default_value is not None:
            # dataset not ready / in workflow / etc
            if self.need_late_validation( trans, context ):
                return UnvalidatedValue( self.default_value )
            return self.default_value
        return SelectToolParameter.get_initial_value( self, trans, context )

    def get_legal_values( self, trans, other_values ):
        return set( self.get_column_list( trans, other_values ) )

    def get_dependencies( self ):
        return [ self.data_ref ]

    def need_late_validation( self, trans, context ):
        if super( ColumnListParameter, self ).need_late_validation( trans, context ):
            return True
        if self.data_ref not in context:
            return False
        # Get the selected dataset if selected
        dataset = context[ self.data_ref ]
        if dataset:
            # Check if the dataset does not have the expected metadata for columns
            if not dataset.metadata.columns:
                # Only allow late validation if the dataset is not yet ready
                # (since we have reason to expect the metadata to be ready eventually)
                if dataset.is_pending or not dataset.datatype.matches_any( self.ref_input.formats ):
                    return True
        # No late validation
        return False

    def to_dict( self, trans, view='collection', value_mapper=None ):
        # call parent to_dict
        d = super( ColumnListParameter, self ).to_dict( trans )

        # add data reference
        d['data_ref'] = self.data_ref
        
        # add numerical flag
        d['numerical'] = self.numerical
        
        # return
        return d


class DrillDownSelectToolParameter( SelectToolParameter ):
    """
    Parameter that takes on one (or many) of a specific set of values.
    Creating a hierarchical select menu, which allows users to 'drill down' a tree-like set of options.

    >>> p = DrillDownSelectToolParameter( None, XML(
    ... '''
    ... <param name="some_name" type="drill_down" display="checkbox" hierarchy="recurse" multiple="true">
    ...   <options>
    ...    <option name="Heading 1" value="heading1">
    ...        <option name="Option 1" value="option1"/>
    ...        <option name="Option 2" value="option2"/>
    ...        <option name="Heading 1" value="heading1">
    ...          <option name="Option 3" value="option3"/>
    ...          <option name="Option 4" value="option4"/>
    ...        </option>
    ...    </option>
    ...    <option name="Option 5" value="option5"/>
    ...   </options>
    ... </param>
    ... ''' ) )
    >>> print p.get_html()
    <div class="form-row drilldown-container" id="drilldown--736f6d655f6e616d65">
    <div class="form-row-input">
    <div><span class="form-toggle icon-button toggle-expand" id="drilldown--736f6d655f6e616d65-68656164696e6731-click"></span>
    <input type="checkbox" name="some_name" value="heading1" >Heading 1
    </div><div class="form-row" id="drilldown--736f6d655f6e616d65-68656164696e6731-container" style="float: left; margin-left: 1em;">
    <div class="form-row-input">
    <input type="checkbox" name="some_name" value="option1" >Option 1
    </div>
    <div class="form-row-input">
    <input type="checkbox" name="some_name" value="option2" >Option 2
    </div>
    <div class="form-row-input">
    <div><span class="form-toggle icon-button toggle-expand" id="drilldown--736f6d655f6e616d65-68656164696e6731-68656164696e6731-click"></span>
    <input type="checkbox" name="some_name" value="heading1" >Heading 1
    </div><div class="form-row" id="drilldown--736f6d655f6e616d65-68656164696e6731-68656164696e6731-container" style="float: left; margin-left: 1em;">
    <div class="form-row-input">
    <input type="checkbox" name="some_name" value="option3" >Option 3
    </div>
    <div class="form-row-input">
    <input type="checkbox" name="some_name" value="option4" >Option 4
    </div>
    </div>
    </div>
    </div>
    </div>
    <div class="form-row-input">
    <input type="checkbox" name="some_name" value="option5" >Option 5
    </div>
    </div>
    >>> p = DrillDownSelectToolParameter( None, XML(
    ... '''
    ... <param name="some_name" type="drill_down" display="radio" hierarchy="recurse" multiple="false">
    ...   <options>
    ...    <option name="Heading 1" value="heading1">
    ...        <option name="Option 1" value="option1"/>
    ...        <option name="Option 2" value="option2"/>
    ...        <option name="Heading 1" value="heading1">
    ...          <option name="Option 3" value="option3"/>
    ...          <option name="Option 4" value="option4"/>
    ...        </option>
    ...    </option>
    ...    <option name="Option 5" value="option5"/>
    ...   </options>
    ... </param>
    ... ''' ) )
    >>> print p.get_html()
    <div class="form-row drilldown-container" id="drilldown--736f6d655f6e616d65">
    <div class="form-row-input">
    <div><span class="form-toggle icon-button toggle-expand" id="drilldown--736f6d655f6e616d65-68656164696e6731-click"></span>
    <input type="radio" name="some_name" value="heading1" >Heading 1
    </div><div class="form-row" id="drilldown--736f6d655f6e616d65-68656164696e6731-container" style="float: left; margin-left: 1em;">
    <div class="form-row-input">
    <input type="radio" name="some_name" value="option1" >Option 1
    </div>
    <div class="form-row-input">
    <input type="radio" name="some_name" value="option2" >Option 2
    </div>
    <div class="form-row-input">
    <div><span class="form-toggle icon-button toggle-expand" id="drilldown--736f6d655f6e616d65-68656164696e6731-68656164696e6731-click"></span>
    <input type="radio" name="some_name" value="heading1" >Heading 1
    </div><div class="form-row" id="drilldown--736f6d655f6e616d65-68656164696e6731-68656164696e6731-container" style="float: left; margin-left: 1em;">
    <div class="form-row-input">
    <input type="radio" name="some_name" value="option3" >Option 3
    </div>
    <div class="form-row-input">
    <input type="radio" name="some_name" value="option4" >Option 4
    </div>
    </div>
    </div>
    </div>
    </div>
    <div class="form-row-input">
    <input type="radio" name="some_name" value="option5" >Option 5
    </div>
    </div>
    >>> print p.options
    [{'selected': False, 'name': 'Heading 1', 'value': 'heading1', 'options': [{'selected': False, 'name': 'Option 1', 'value': 'option1', 'options': []}, {'selected': False, 'name': 'Option 2', 'value': 'option2', 'options': []}, {'selected': False, 'name': 'Heading 1', 'value': 'heading1', 'options': [{'selected': False, 'name': 'Option 3', 'value': 'option3', 'options': []}, {'selected': False, 'name': 'Option 4', 'value': 'option4', 'options': []}]}]}, {'selected': False, 'name': 'Option 5', 'value': 'option5', 'options': []}]
    """
    def __init__( self, tool, elem, context=None ):
        def recurse_option_elems( cur_options, option_elems ):
            for option_elem in option_elems:
                selected = string_as_bool( option_elem.get( 'selected', False ) )
                cur_options.append( { 'name':option_elem.get( 'name' ), 'value': option_elem.get( 'value'), 'options':[], 'selected':selected  } )
                recurse_option_elems( cur_options[-1]['options'], option_elem.findall( 'option' ) )
        ToolParameter.__init__( self, tool, elem )
        self.multiple = string_as_bool( elem.get( 'multiple', False ) )
        self.display = elem.get( 'display', None )
        self.hierarchy = elem.get( 'hierarchy', 'exact' ) #exact or recurse
        self.separator = elem.get( 'separator', ',' )
        from_file = elem.get( 'from_file', None )
        if from_file:
            if not os.path.isabs( from_file ):
                from_file = os.path.join( tool.app.config.tool_data_path, from_file )
            elem = XML( "<root>%s</root>" % open( from_file ).read() )
        self.is_dynamic = False
        self.dynamic_options = elem.get( 'dynamic_options' , None )
        if self.dynamic_options:
            self.is_dynamic = True
        self.options = []
        self.filtered = {}
        if elem.find( 'filter' ):
            self.is_dynamic = True
            for filter in elem.findall( 'filter' ):
                #currently only filtering by metadata key matching input file is allowed
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
        call_other_values = { '__trans__': trans, '__value__': value }
        if other_values:
            call_other_values.update( other_values.dict )
        return eval( self.dynamic_options, self.tool.code_namespace, call_other_values )

    def get_options( self, trans=None, value=None, other_values={} ):
        if self.is_dynamic:
            if self.dynamic_options:
                options = self._get_options_from_code( trans=trans, value=value, other_values=other_values )
            else:
                options = []
            for filter_key, filter_value in self.filtered.iteritems():
                dataset = other_values[filter_key]
                if dataset.__class__.__name__.endswith( "DatasetFilenameWrapper" ):  # this is a bad way to check for this, but problems importing class ( due to circular imports? )
                    dataset = dataset.dataset
                if dataset:
                    for meta_key, meta_dict in filter_value.iteritems():
                        check_meta_val = dataset.metadata.spec[meta_key].param.to_string( dataset.metadata.get( meta_key ) )
                        if check_meta_val in meta_dict:
                            options.extend( meta_dict[check_meta_val] )
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

    def get_html( self, trans=None, value=None, other_values={} ):
        """
        Returns the html widget corresponding to the paramter.
        Optionally attempt to retain the current value specific by 'value'
        """
        return self.get_html_field( trans, value, other_values ).get_html()

    def get_html_field( self, trans=None, value=None, other_values={} ):
        # Dynamic options are not yet supported in workflow, allow
        # specifying the value as text for now.
        if self.need_late_validation( trans, other_values ):
            if value is not None:
                assert isinstance( value, UnvalidatedValue ), "Late validation needed for '%s', but provided value (%s) is not of type UnvalidatedValue (%s)." % ( self.name, value, type( value ) )
                value = value.value
            if self.multiple:
                if value is None:
                    value = ""
                else:
                    value = "\n".join( value )
                return form_builder.TextArea( self.name, value=value )
            else:
                return form_builder.TextField( self.name, value=(value or "") )
        return form_builder.DrillDownField( self.name, self.multiple, self.display, self.refresh_on_change, self.get_options( trans, value, other_values ), value, refresh_on_change_values = self.refresh_on_change_values )

    def from_html( self, value, trans=None, other_values={} ):
        if self.need_late_validation( trans, other_values ):
            if self.multiple:
                if value == '': #No option selected
                    value = None
                else:
                    value = value.split( "\n" )
            return UnvalidatedValue( value )
        if not value: return None
        if not isinstance( value, list ):
            value = [value]
        if not( self.repeat ) and len( value ) > 1:
            assert self.multiple, "Multiple values provided but parameter is not expecting multiple values"
        rval = []
        for val in value:
            if val not in self.get_legal_values( trans, other_values ): raise ValueError( "An invalid option was selected, please verify" )
            rval.append( val )
        return rval

    def to_param_dict_string( self, value, other_values={}, value_map=DEFAULT_VALUE_MAP ):
        def get_options_list( value ):
            def get_base_option( value, options ):
                for option in options:
                    if value == option['value']:
                        return option
                    rval = get_base_option( value, option['options'] )
                    if rval: return rval
                return None #not found
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
        if len( rval ) > 1:
            if not( self.repeat ):
                assert self.multiple, "Multiple values provided but parameter is not expecting multiple values"
        rval = self.separator.join( map( value_map, rval ) )
        if self.tool is None or self.tool.options.sanitize:
            if self.sanitizer:
                rval = self.sanitizer.sanitize_param( rval )
            else:
                rval = sanitize_param( rval )
        return rval

    def get_initial_value( self, trans, context, history=None ):
        def recurse_options( initial_values, options ):
            for option in options:
                if option['selected']:
                    initial_values.append( option['value'] )
                recurse_options( initial_values, option['options'] )
        # More working around dynamic options for workflow
        if self.need_late_validation( trans, context ):
            # Really the best we can do?
            return UnvalidatedValue( None )
        initial_values = []
        recurse_options( initial_values, self.get_options( trans=trans, other_values=context ) )
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

        if isinstance( value, UnvalidatedValue ):
            suffix = "\n(value not yet validated)"
            value = value.value
        else:
            suffix = ""
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
        return "\n".join( map( str, rval ) ) + suffix

    def get_dependencies( self ):
        """
        Get the *names* of the other params this param depends on.
        """
        return self.filtered.keys()

    def to_dict( self, trans, view='collection', value_mapper=None ):
        # skip SelectToolParameter (the immediate parent) bc we need to get options in a different way here
        d = ToolParameter.to_dict( self, trans )

        options = []
        try:
            options = self.get_options( trans, {} )
        except KeyError:
            # will sometimes error if self.is_dynamic and self.filtered
            #   bc we dont/cant fill out other_values above ({})
            pass

        d[ 'options' ] = options
        return d


class DummyDataset( object ):
    pass


class BaseDataToolParameter( ToolParameter ):

    def __init__( self, tool, elem, trans ):
        super(BaseDataToolParameter, self).__init__( tool, elem )

    def _get_history( self, trans, history=None ):
        class_name = self.__class__.__name__
        assert trans is not None, "%s requires a trans" % class_name
        if history is None:
            history = trans.get_history()
        assert history is not None, "%s requires a history" % class_name
        return history

    def _ensure_selection( self, field ):
        set_selected = field.get_selected( return_label=True, return_value=True, multi=False ) is not None
        # Ensure than an item is always selected
        if self.optional:
            if set_selected:
                field.add_option( "Selection is Optional", 'None', False )
            else:
                field.add_option( "Selection is Optional", 'None', True )
        elif not set_selected and bool( field.options ):
            # Select the last item
            a, b, c = field.options[-1]
            field.options[-1] = a, b, True

    def _datatypes_registery( self, trans, tool ):
        # Find datatypes_registry
        if tool is None:
            if trans:
                # Must account for "Input Dataset" types, which while not a tool still need access to the real registry.
                # A handle to the transaction (and thus app) will be given by the module.
                datatypes_registry = trans.app.datatypes_registry
            else:
                #This occurs for things such as unit tests
                import galaxy.datatypes.registry
                datatypes_registry = galaxy.datatypes.registry.Registry()
                datatypes_registry.load_datatypes()
        else:
            datatypes_registry = tool.app.datatypes_registry
        return datatypes_registry

    def _parse_formats( self, trans, tool, elem ):
        datatypes_registry = self._datatypes_registery( trans, tool )

        # Build tuple of classes for supported data formats
        formats = []
        self.extensions = elem.get( 'format', 'data' ).split( "," )
        normalized_extensions = [extension.strip().lower() for extension in self.extensions]
        for extension in normalized_extensions:
            formats.append( datatypes_registry.get_datatype_by_extension( extension ) )
        self.formats = formats

    def _parse_options( self, elem ):
        # TODO: Enhance dynamic options for DataToolParameters. Currently,
        #       only the special case key='build' of type='data_meta' is
        #       a valid filter
        options = elem.find( 'options' )
        if options is None:
            self.options = None
            self.options_filter_attribute = None
        else:
            self.options = dynamic_options.DynamicOptions( options, self )

            #HACK to get around current hardcoded limitation of when a set of dynamic options is defined for a DataToolParameter
            #it always causes available datasets to be filtered by dbkey
            #this behavior needs to be entirely reworked (in a backwards compatible manner)
            self.options_filter_attribute = options.get(  'options_filter_attribute', None )
        self.is_dynamic = self.options is not None

    def _switch_fields( self, fields, default_field ):
        if len(fields) > 1:
            field = form_builder.SwitchingSelectField( fields, default_field=default_field )
        else:
            field = fields.values()[0]
        return field


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

    def __init__( self, tool, elem, trans=None):
        super(DataToolParameter, self).__init__( tool, elem, trans )
        # Add metadata validator
        if not string_as_bool( elem.get( 'no_validation', False ) ):
            self.validators.append( validation.MetadataValidator() )
        self._parse_formats( trans, tool, elem )
        self.multiple = string_as_bool( elem.get( 'multiple', False ) )
        self._parse_options( elem )
        # Load conversions required for the dataset input
        self.conversions = []
        for conv_elem in elem.findall( "conversion" ):
            name = conv_elem.get( "name" )  # name for commandline substitution
            conv_extensions = conv_elem.get( "type" )  # target datatype extension
            # FIXME: conv_extensions should be able to be an ordered list
            assert None not in [ name, type ], 'A name (%s) and type (%s) are required for explicit conversion' % ( name, type )
            conv_types = [ tool.app.datatypes_registry.get_datatype_by_extension( conv_extensions.lower() ) ]
            self.conversions.append( ( name, conv_extensions, conv_types ) )

    def get_html_field( self, trans=None, value=None, other_values={} ):
        if value is not None:
            if type( value ) != list:
                value = [ value ]

        history = self._get_history( trans )
        dataset_matcher = DatasetMatcher( trans, self, value, other_values )
        multiple = self.multiple
        fields = odict()
        if multiple:
            # Select one dataset, run one job.
            default_field = "multiselect_single"
            multi_select = self._get_select_dataset_field( history, dataset_matcher, multiple=True )
            fields[ "multiselect_single" ] = multi_select

            if self.__display_multirun_option():
                collection_select = self._get_select_dataset_collection_fields( history, dataset_matcher, suffix="", reduction=True )
                if collection_select.get_selected(return_value=True):
                    default_field = "multiselect_collection"
                fields[ "multiselect_collection" ] = collection_select
                self._ensure_selection( collection_select )

        else:
            # Select one dataset, run one job.
            default_field = "select_single"
            single_select = self._get_select_dataset_field( history, dataset_matcher, multiple=False )
            fields[ "select_single" ] = single_select

            if self.__display_multirun_option():
                # Select multiple datasets, run multiple jobs.
                multirun_key = "%s|__multirun__" % self.name
                collection_multirun_key = "%s|__collection_multirun__" % self.name
                if multirun_key in (other_values or {}):
                    multirun_value = listify( other_values[ multirun_key ] )
                    if multirun_value and len( multirun_value ) > 1:
                        default_field = "select_multiple"
                elif collection_multirun_key in (other_values or {}):
                    multirun_value = listify( other_values[ collection_multirun_key ] )
                    if multirun_value:
                        default_field = "select_collection"
                else:
                    multirun_value = value
                multi_dataset_matcher = DatasetMatcher( trans, self, multirun_value, other_values )
                multi_select = self._get_select_dataset_field( history, multi_dataset_matcher, multiple=True, suffix="|__multirun__" )
                fields[ "select_multiple" ] = multi_select
                collection_field = self._get_select_dataset_collection_fields( history, dataset_matcher, multiple=False, reduction=False )
                fields[ "select_collection" ] = collection_field

        return self._switch_fields( fields, default_field=default_field )

    def _get_select_dataset_collection_fields( self, history, dataset_matcher, multiple=False, suffix="|__collection_multirun__", reduction=False ):
        if not reduction:
            value_modifier = lambda x: x
        else:
            value_modifier = lambda value: "__collection_reduce__|%s" % value

        value = dataset_matcher.value
        if value is not None:
            if type( value ) != list:
                value = [ value ]

        field_name = "%s%s" % ( self.name, suffix )
        field = form_builder.SelectField( field_name, multiple, None, self.refresh_on_change, refresh_on_change_values=self.refresh_on_change_values )

        dataset_collection_matcher = DatasetCollectionMatcher( dataset_matcher )

        for history_dataset_collection in history.active_dataset_collections:
            if dataset_collection_matcher.hdca_match( history_dataset_collection, reduction=reduction ):
                name = history_dataset_collection.name
                hid = str( history_dataset_collection.hid )
                hidden_text = ""  # TODO
                id = value_modifier( dataset_matcher.trans.security.encode_id( history_dataset_collection.id ) )
                selected = value and history_dataset_collection in value
                text = "%s:%s %s" % ( hid, hidden_text, name )
                field.add_option( text, id, selected )

        return field

    def _get_select_dataset_field( self, history, dataset_matcher, multiple=False, suffix="" ):

        # CRUCIAL: the dataset_collector function needs to be local to DataToolParameter.get_html_field()
        def dataset_collector( hdas, parent_hid ):
            for i, hda in enumerate( hdas ):
                hda_name = hda.name
                if parent_hid is not None:
                    hid = "%s.%d" % ( parent_hid, i + 1 )
                else:
                    hid = str( hda.hid )
                hda_match = dataset_matcher.hda_match( hda )
                if not hda_match:
                    continue
                if not hda_match.implicit_conversion:
                    selected = dataset_matcher.selected( hda )
                    if hda.visible:
                        hidden_text = ""
                    else:
                        hidden_text = " (hidden)"
                    field.add_option( "%s:%s %s" % ( hid, hidden_text, hda_name ), hda.id, selected )
                else:
                    hda = hda_match.hda  # Get converted dataset
                    target_ext = hda_match.target_ext
                    selected = dataset_matcher.selected( hda )
                    field.add_option( "%s: (as %s) %s" % ( hid, target_ext, hda_name ), hda.id, selected )
                # Also collect children via association object
                dataset_collector( hda.children, hid )

        field_name = "%s%s" % ( self.name, suffix )
        field = form_builder.SelectField( field_name, multiple, None, self.refresh_on_change, refresh_on_change_values=self.refresh_on_change_values )

        dataset_collector( history.active_datasets_children_and_roles, None )
        self._ensure_selection( field )
        return field

    def get_initial_value( self, trans, context, history=None ):
        return self.get_initial_value_from_history_prevent_repeats(trans, context, None, history=history)

    def get_initial_value_from_history_prevent_repeats( self, trans, context, already_used, history=None ):
        """
        NOTE: This is wasteful since dynamic options and dataset collection
              happens twice (here and when generating HTML).
        """
        # Can't look at history in workflow mode. Tool shed has no histories.
        if trans is None or trans.workflow_building_mode or trans.webapp.name == 'tool_shed':
            return DummyDataset()
        history = self._get_history( trans, history )
        dataset_matcher = DatasetMatcher( trans, self, None, context )
        if self.optional:
            return None
        most_recent_dataset = []

        def dataset_collector( datasets ):
            for i, data in enumerate( datasets ):
                if data.visible and dataset_matcher.hda_accessible( data, check_security=False ):
                    match = dataset_matcher.valid_hda_match( data, check_security=False )
                    if not match or dataset_matcher.filter( match.hda ):
                        continue
                    data = match.hda
                    most_recent_dataset.append(data)
                # Also collect children via association object
                dataset_collector( data.children )
        dataset_collector( history.active_datasets_children_and_roles )
        most_recent_dataset.reverse()
        if already_used is not None:
            for val in most_recent_dataset:
                if val is not None and val not in already_used:
                    already_used.append(val)
                    return val
        if len(most_recent_dataset) > 0:
            return most_recent_dataset[0]
        return ''

    def from_html( self, value, trans, other_values={} ):
        # Can't look at history in workflow mode, skip validation and such,
        # although, this should never be called in workflow mode right?
        if trans.workflow_building_mode:
            return None
        if not value and not self.optional:
            raise ValueError( "History does not include a dataset of the required format / build" )
        if value in [None, "None"]:
            return None
        if isinstance( value, str ) and value.find( "," ) > 0:
            value = [ int( value_part ) for value_part in  value.split( "," ) ]
        if isinstance( value, list ):
            rval = []
            for single_value in value:
                if isinstance( single_value, dict ):
                    assert single_value['src'] == 'hda'
                    rval.append( trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( trans.app.security.decode_id( single_value[ 'id' ] ) ) )
                else:
                    rval.append( trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( single_value ) )
        elif isinstance( value, trans.app.model.HistoryDatasetAssociation ):
            rval = value
        elif isinstance( value, dict ) and 'src' in value and 'id' in value:
            if value['src'] == 'hda':
                rval = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( trans.app.security.decode_id(value['id']) )
            elif value['src'] == 'hdca':
                decoded_id = trans.app.security.decode_id( value[ 'id' ] )
                rval = trans.sa_session.query( trans.app.model.HistoryDatasetCollectionAssociation ).get( decoded_id )
            else:
                raise ValueError("Unknown input source %s passed to job submission API." % value['src'])
        elif str( value ).startswith( "__collection_reduce__|" ):
            encoded_id = str( value )[ len( "__collection_reduce__|" ): ]
            decoded_id = trans.app.security.decode_id( encoded_id )
            rval = trans.sa_session.query( trans.app.model.HistoryDatasetCollectionAssociation ).get( decoded_id )
        else:
            rval = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( value )
        if isinstance( rval, list ):
            values = rval
        else:
            values = [ rval ]
        for v in values:
            if v:
                if v.deleted:
                    raise ValueError( "The previously selected dataset has been previously deleted" )
                if hasattr( v, "dataset" ) and v.dataset.state in [ galaxy.model.Dataset.states.ERROR, galaxy.model.Dataset.states.DISCARDED ]:
                    raise ValueError( "The previously selected dataset has entered an unusable state" )
        if not self.multiple:
            if len( values ) > 1:
                raise ValueError( "More than one dataset supplied to single input dataset parameter.")
            rval = values[ 0 ]
        return rval

    def to_string( self, value, app ):
        if value is None or isinstance( value, basestring ):
            return value
        elif isinstance( value, int ):
            return str( value )
        elif isinstance( value, DummyDataset ):
            return None
        elif isinstance( value, list) and len(value) > 0 and isinstance( value[0], DummyDataset):
            return None
        elif isinstance( value, list ):
            return ",".join( [ str( self.to_string( val, app ) ) for val in value ] )
        elif isinstance( value, app.model.HistoryDatasetCollectionAssociation ):
            return "__collection_reduce__|%s" % app.security.encode_id( value.id )
        try:
            return value.id
        except:
            return str( value )

    def to_python( self, value, app ):
        # Both of these values indicate that no dataset is selected.  However, 'None'
        # indicates that the dataset is optional, while '' indicates that it is not.
        none_values = [ None, '', 'None' ]
        if value in none_values:
            return value
        if isinstance(value, str) and value.find(",") > -1:
            values = value.split(",")
            # TODO: Optimize. -John
            return [ app.model.context.query( app.model.HistoryDatasetAssociation ).get( int( val ) ) for val in values if val not in none_values ]
        # Not sure if following case is needed, if yes deduplicate with above code.
        elif str( value ).startswith( "__collection_reduce__|" ):
            # When coming from HTML this id would be encoded, in database it
            # really should be decoded however.
            decoded_id = str( value )[ len( "__collection_reduce__|" ): ]
            return app.model.context.query( app.model.HistoryDatasetCollectionAssociation ).get( decoded_id )
        return app.model.context.query( app.model.HistoryDatasetAssociation ).get( int( value ) )

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
        return "No dataset"

    def validate( self, value, history=None ):
        for validator in self.validators:
            if value and self.multiple:
                if isinstance(value, list):
                    for v in value:
                        validator.validate( v, history )
                elif isinstance(value, galaxy.model.HistoryDatasetCollectionAssociation):
                    for v in value.collection.dataset_instances:
                        validator.validate( v, history )
            else:
                validator.validate( value, history )

    def need_late_validation( self, trans, context ):
        if trans is None or trans.workflow_building_mode:
            return True
        return False

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

    def __display_multirun_option( self ):
        """ Certain parameters may not make sense to allow multi-run variants
        of for instance if other parameters are filtered or contrained based on
        this one. TODO: Figure out if these exist and how to detect them (
        for instance should I just be checking dynamic options).
        """
        allow = True
        # TODO: allow should be false in some in cases...
        return allow

    def _options_filter_attribute( self, value ):
        #HACK to get around current hardcoded limitation of when a set of dynamic options is defined for a DataToolParameter
        #it always causes available datasets to be filtered by dbkey
        #this behavior needs to be entirely reworked (in a backwards compatible manner)
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

    def to_dict( self, trans, view='collection', value_mapper=None ):
        d = super( DataToolParameter, self ).to_dict( trans )
        d['extensions'] = self.extensions
        d['multiple'] = self.multiple
        return d

class DataCollectionToolParameter( BaseDataToolParameter ):
    """
    """

    def __init__( self, tool, elem, trans=None ):
        super(DataCollectionToolParameter, self).__init__( tool, elem, trans )
        self.elem = elem
        self._parse_formats( trans, tool, elem )
        self.multiple = False  # Accessed on DataToolParameter a lot, may want in future
        self._parse_options( elem )  # TODO: Review and test.

    @property
    def collection_type( self ):
        return self.elem.get( "collection_type", None )

    def _history_query( self, trans ):
        dataset_collection_type_descriptions = trans.app.dataset_collections_service.collection_type_descriptions
        return history_query.HistoryQuery.from_parameter_elem( self.elem, dataset_collection_type_descriptions )

    def get_html_field( self, trans=None, value=None, other_values={} ):
        # dropped refresh values, may be needed..
        default_field = "select_single_collection"
        fields = odict()

        collection_multirun_key = "%s|__collection_multirun__" % self.name
        if collection_multirun_key in (other_values or {}):
            multirun_value = other_values[ collection_multirun_key ]
            if multirun_value:
                default_field = "select_map_over_collections"
        else:
            multirun_value = value

        history = self._get_history( trans )
        fields[ "select_single_collection" ] = self._get_single_collection_field( trans=trans, history=history, value=value, other_values=other_values )
        fields[ "select_map_over_collections" ] = self._get_select_dataset_collection_field( trans=trans, history=history, value=multirun_value, other_values=other_values )

        return self._switch_fields( fields, default_field=default_field )

    def _get_single_collection_field( self, trans, history, value, other_values ):
        field = form_builder.SelectField( self.name, self.multiple, None, self.refresh_on_change, refresh_on_change_values=self.refresh_on_change_values )
        dataset_collections = trans.app.dataset_collections_service.history_dataset_collections( history, self._history_query( trans ) )
        dataset_matcher = DatasetMatcher( trans, self, value, other_values )
        dataset_collection_matcher = DatasetCollectionMatcher( dataset_matcher )

        for dataset_collection_instance in dataset_collections:
            if not dataset_collection_matcher.hdca_match( dataset_collection_instance ):
                continue
            instance_id = dataset_collection_instance.hid
            instance_name = dataset_collection_instance.name
            selected = ( value and ( dataset_collection_instance == value ) )
            if dataset_collection_instance.visible:
                hidden_text = ""
            else:
                hidden_text = " (hidden)"
            field.add_option( "%s:%s %s" % ( instance_id, hidden_text, instance_name ), dataset_collection_instance.id, selected )
        self._ensure_selection( field )
        return field

    def _get_select_dataset_collection_field( self, trans, history, multiple=False, suffix="|__collection_multirun__", value=None, other_values=None ):
        field_name = "%s%s" % ( self.name, suffix )
        field = form_builder.SelectField( field_name, multiple, None, self.refresh_on_change, refresh_on_change_values=self.refresh_on_change_values )
        dataset_matcher = DatasetMatcher( trans, self, value, other_values )
        dataset_collection_matcher = DatasetCollectionMatcher( dataset_matcher )

        for history_dataset_collection in history.active_dataset_collections:
            if not self._history_query( trans ).can_map_over( history_dataset_collection ):
                continue

            datasets_match = dataset_collection_matcher.hdca_match( history_dataset_collection )
            if datasets_match:
                name = history_dataset_collection.name
                hid = str( history_dataset_collection.hid )
                hidden_text = ""  # TODO
                subcollection_type = self._history_query( trans ).collection_type_description.collection_type
                id = "%s|%s" % ( dataset_matcher.trans.security.encode_id( history_dataset_collection.id ), subcollection_type )
                text = "%s:%s %s" % ( hid, hidden_text, name )

                field.add_option( text, id, False )

        return field

    def from_html( self, value, trans, other_values={} ):
        if not value and not self.optional:
            raise ValueError( "History does not include a dataset collection of the correct type or containing the correct types of datasets" )
        if value in [None, "None"]:
            return None
        if isinstance( value, str ) and value.find( "," ) > 0:
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
                rval = trans.sa_session.query( trans.app.model.HistoryDatasetCollectionAssociation ).get( trans.app.security.decode_id(value['id']) )
        elif isinstance( value, basestring ):
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

    def to_string( self, value, app ):
        if value is None or isinstance( value, basestring ):
            return value
        elif isinstance( value, DummyDataset ):
            return None
        try:
            if isinstance( value, galaxy.model.DatasetCollectionElement ):
                return "dce:%s" % value.id
            else:
                return "hdca:%s" % value.id
        except Exception:
            # This is not good...
            return str( value )

    def to_python( self, value, app ):
        # Both of these values indicate that no dataset is selected.  However, 'None'
        # indicates that the dataset is optional, while '' indicates that it is not.
        if value is None or value == '' or value == 'None':
            return value

        if not isinstance( value, basestring ):
            raise ValueError( "Can not convert data collection parameter value to python object - %s" % value )

        if value.startswith( "dce:" ):
            dce = app.model.context.query( app.model.DatasetCollectionElement ).get( int( value[ len( "dce:" ): ] ) )
            return dce
        elif value.startswith( "hdca:" ):
            hdca = app.model.context.query( app.model.HistoryDatasetCollectionAssociation ).get( int( value[ len( "hdca:" ): ] ) )
            return hdca
        else:
            raise ValueError( "Can not convert data collection parameter value to python object - %s" % value )

    def value_to_display_text( self, value, app ):
        try:
            if isinstance( value, galaxy.model.HistoryDatasetCollectionAssociation ):
                display_text = "%s: %s" % ( value.hid, value.name )
            else:
                display_text = "Element %d:%s" % ( value.identifier_index, value.identifier_name )
        except AttributeError:
            display_text = "No dataset collection."
        return display_text

    def validate( self, value, history=None ):
        return True  # TODO


class HiddenDataToolParameter( HiddenToolParameter, DataToolParameter ):
    """
    Hidden parameter that behaves as a DataToolParameter. As with all hidden
    parameters, this is a HACK.
    """
    def __init__( self, tool, elem ):
        DataToolParameter.__init__( self, tool, elem )
        self.value = "None"
        self.type = "hidden_data"

    def get_initial_value( self, trans, context, history=None ):
        return None

    def get_html_field( self, trans=None, value=None, other_values={} ):
        return form_builder.HiddenField( self.name, self.value )


class LibraryDatasetToolParameter( ToolParameter ):
    """
    Parameter that lets users select a LDDA from a modal window, then use it within the wrapper.
    """

    def __init__( self, tool, elem ):
        ToolParameter.__init__( self, tool, elem )

    def get_html_field( self, trans=None, value=None, other_values={} ):
        return form_builder.LibraryField( self.name, value=value, trans=trans )

    def get_initial_value( self, trans, context ):
        return None

    def from_html( self, value, trans, other_values={} ):
        if not value:
            return None
        elif isinstance( value, list ):
            return value
        else:
            decoded_lst = []
            for encoded_id in value.split("||"):
                decoded_lst.append( trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ).get( trans.security.decode_id( encoded_id ) ) )
            return decoded_lst

    def to_string( self, value, app ):
        if not value:
            return value
        return [ldda.id for ldda in value]

    def to_python( self, value, app ):
        if not value:
            return value
        lddas = []
        for ldda_id in value:
            lddas.append( app.model.context.query( app.model.LibraryDatasetDatasetAssociation ).get( ldda_id ) )
        return lddas

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
#     >>> from galaxy.model import History
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
#     def get_html( self, trans, value=None, other_values={} ):
#         assert trans.history is not None, "HistoryIDParameter requires a history"
#         self.html = form_builder.HiddenField( self.name, trans.history.id ).get_html()
#         return self.html

parameter_types = dict(
    text=TextToolParameter,
    integer=IntegerToolParameter,
    float=FloatToolParameter,
    boolean=BooleanToolParameter,
    genomebuild=GenomeBuildParameter,
    select=SelectToolParameter,
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


class UnvalidatedValue( object ):
    """
    Wrapper to mark a value that has not been validated
    """
    def __init__( self, value ):
        self.value = value

    def __str__( self ):
        return str( self.value )


class RuntimeValue( object ):
    """
    Wrapper to note a value that is not yet set, but will be required at
    runtime.
    """
    pass
