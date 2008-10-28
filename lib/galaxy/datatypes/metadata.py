import sys, logging, copy, shutil, weakref

from galaxy.util import string_as_bool
from galaxy.util.odict import odict
from galaxy.web import form_builder
import galaxy.model

log = logging.getLogger( __name__ )

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


class MetadataCollection:
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
                return self.spec[name].wrap( self.parent._metadata[name] )
            return self.spec[name].wrap( self.spec[name].default )
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
            return self.spec[name].param.get_html( value=getattr( self, name ), context=self, **kwd )
    def make_dict_copy( self, to_copy ):
        """Makes a deep copy of input iterable to_copy according to self.spec"""
        rval = {}
        for key, value in to_copy.items():
            if key in self.spec:
                rval[key] = self.spec[key].param.make_copy( value, target_context=self, source_context=to_copy )
        return rval

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

class MetadataParameter( object ):
    def __init__( self, spec ):
        self.spec = spec
        
    def get_html_field( self, value=None, context={}, other_values={}, **kwd ):
        return form_builder.TextField( self.spec.name, value=value )
    
    def get_html( self, value, context={}, other_values={}, **kwd ):
        """
        The "context" is simply the metadata collection/bunch holding
        this piece of metadata. This is passed in to allow for
        metadata to validate against each other (note: this could turn
        into a huge, recursive mess if not done with care). For
        example, a column assignment should validate against the
        number of columns in the dataset.
        """
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
    
    def wrap( self, value ):
        """
        Turns a value into its usable form.
        """
        return value

class MetadataElementSpec( object ):
    """
    Defines a metadata element and adds it to the metadata_spec (which
    is a MetadataSpecCollection) of datatype.
    """

    def __init__( self, datatype, name=None, desc=None, param=MetadataParameter, default=None, no_value = None, visible=True, **kwargs ):
        self.name = name
        self.desc = desc or name
        self.default = default
        self.no_value = no_value
        self.visible = visible
        # Catch-all, allows for extra attributes to be set
        self.__dict__.update(kwargs)
        #set up param last, as it uses values set above
        self.param = param( self )
        datatype.metadata_spec.append( self ) #add spec element to the spec
    def get( self, name ):
        return self.__dict__.get(name, None)
    def wrap( self, value ):
        """
        Turns a stored value into its usable form.
        """
        return self.param.wrap( value )
    def unwrap( self, value ):
        """
        Turns an incoming value into its storable form.
        """
        return self.param.unwrap( value )

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
    
    def get_html_field( self, value=None, context={}, other_values={}, values=None, **kwd ):
        field = form_builder.SelectField( self.spec.name, multiple=self.multiple, display=self.spec.get("display") )
        for val, label in self.values or values or [(val2, val2) for val2 in value]:
            try:
                if ( self.multiple and val in value ) or ( not self.multiple and val == value ):
                    field.add_option( label, val, selected=True )
                else:
                    field.add_option( label, val, selected=False )
            except TypeError:
                field.add_option( val, label, selected=False )

        return field

    def get_html( self, value, context={}, other_values={}, values=None, **kwd ):
        if self.spec.get("readonly"):
            if value in [ None, [] ]:
                return str( self.spec.no_value )
            return ", ".join( map( str, value ) )
        return MetadataParameter.get_html( self, value, context=context, other_values=other_values, values=values, **kwd )

    def wrap( self, value ):
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
    
class RangeParameter( SelectParameter ):
    def __init__( self, spec ):
        SelectParameter.__init__( self, spec )
        # The spec must be set with min and max values
        self.min = spec.get( "min" ) or 1
        self.max = spec.get( "max" ) or 1
        self.step = self.spec.get( "step" ) or 1

    def get_html_field( self, value=None, context={}, other_values={}, values=None, **kwd ):
        if values is None:
            values = zip( range( self.min, self.max, self.step ), range( self.min, self.max, self.step ))
        return SelectParameter.get_html_field( self, value=value, context=context, other_values=other_values, values=values, **kwd )
    
    def get_html( self, value, context={}, other_values={}, values=None, **kwd ):
        if values is None:
            values = zip( range( self.min, self.max, self.step ), range( self.min, self.max, self.step ))
        return SelectParameter.get_html( self, value, context=context, other_values=other_values, values=values, **kwd )
    
    @classmethod
    def marshal( cls, value ):
        value = SelectParameter.marshal( value )
        values = [ int(x) for x in value ]
        return values
    
class ColumnParameter( RangeParameter ):
    
    def get_html_field( self, value=None, context={}, other_values={}, values=None, **kwd ):
        if values is None and context:
            column_range = range( 1, context.columns+1, 1 )
            values = zip( column_range, column_range )
        return RangeParameter.get_html_field( self, value=value, context=context, other_values=other_values, values=values, **kwd )
    
    def get_html( self, value, context={}, other_values={}, values=None, **kwd ):
        if values is None and context:
            column_range = range( 1, context.columns+1, 1 )
            values = zip( column_range, column_range )
        return RangeParameter.get_html( self, value, context=context, other_values=other_values, values=values, **kwd ) 
    
class ColumnTypesParameter( MetadataParameter ):
    
    def to_string( self, value ):
        return ",".join( map( str, value ) )

class PythonObjectParameter( MetadataParameter ):
    
    def to_string( self, value ):
        if not value:
            return self.spec._to_string( self.spec.no_value )
        return self.spec._to_string( value )
    
    def get_html_field( self, value=None, context={}, other_values={}, **kwd ):
        return form_builder.TextField( self.spec.name, value=self._to_string( value ) )

    def get_html( self, value=None, context={}, other_values={}, **kwd ):
        return str( self )

    @classmethod
    def marshal( cls, value ):
        return value

class FileParameter( MetadataParameter ):
    
    def to_string( self, value ):
        if not value:
            return str( self.spec.no_value )
        return value.file_name
    
    def get_html_field( self, value=None, context={}, other_values={}, **kwd ):
        return form_builder.TextField( self.spec.name, value=str( value.id ) )

    def get_html( self, value=None, context={}, other_values={}, **kwd ):
        return "<div>No display available for Metadata Files</div>"

    def wrap( self, value ):
        if isinstance( value, galaxy.model.MetadataFile ):
            return value
        try:
            return galaxy.model.MetadataFile.get( value )
        except:
            #value was not a valid id
            return None

    def make_copy( self, value, target_context = None, source_context = None ):
        value = self.wrap( value )
        if value:
            new_value = galaxy.model.MetadataFile( dataset = target_context.parent, name = self.spec.name )
            new_value.flush()
            shutil.copy( value.file_name, new_value.file_name )
            return self.unwrap( new_value )
        return None

    @classmethod
    def marshal( cls, value ):
        if isinstance( value, galaxy.model.MetadataFile ):
            value = value.id
        return value
