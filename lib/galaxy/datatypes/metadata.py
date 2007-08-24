import sys, logging

from galaxy.util.bunch import Bunch
from galaxy.util.odict import odict
from galaxy.web import form_builder

log = logging.getLogger( __name__ )

# Taken in part from Elixir and how they do it: http://elixir.ematia.de

STATEMENTS = "__galaxy_statements__"

class Statement( object ):
    '''
    This class inserts its target into a list in the surrounding
    class.  the data.Data class has a metaclass which executes these
    statements.  This is how we shove the metadata element spec into
    the class.
    '''
    def __init__( self, target ):
        self.target = target
    def __call__( self, *args, **kwargs ):
        class_locals = sys._getframe(1).f_locals
        statements = class_locals.setdefault(STATEMENTS, [])
        statements.append((self, args, kwargs))
    @classmethod
    def process( cls, element ):
        for statement, args, kwargs in getattr( element, STATEMENTS, [] ):
            statement.target( element, *args, **kwargs )

class MetadataSpecCollection( odict ):
    '''
    A simple extension of dict which allows cleaner access to items
    and allows the values to be iterated over directly as if it were a
    list.  append() is also implemented for simplicity and does not
    "append".
    '''
    def __init__(self, dict = None):
        odict.__init__(self, dict = None)
    def append( self, item ):
        self[item.name] = item
    def iter( self ):
        return self.itervalues()
    def __getattr__( self, name ):
        return self.get(name)

class MetadataParameter( object ):
    def __init__( self, spec, value, context ):
        '''
        The "context" is simply the metadata collection/bunch holding
        this piece of metadata. This is passed in to allow for
        metadata to validate against each other (note: this could turn
        into a huge, recursive mess if not done with care). For
        example, a column assignment should validate against the
        number of columns in the dataset.
        '''
        self.spec = spec
        self.value = value
        self.context = context

    def __str__(self):
        if self.value is None:
            return str(self.spec.no_value)
        return str(self.value)

    @classmethod
    def marshal( cls, value ):
        '''
        This method should/can be overridden to convert the incomming
        value to whatever type it is supposed to be.
        '''
        return value

    @classmethod
    def validate( cls, value ):
        '''
        Throw an exception if the value is invalid.
        '''
        pass

    def get_html_field( self, value=None, other_values={} ):
        return form_builder.TextField( self.spec.name, value=value or self.value )

    def get_html( self ):
        if self.spec.get("readonly"):
            return self.value
        if self.spec.get("optional"):
            checked = False
            if self.value: checked = "true"
            checkbox = form_builder.CheckboxField( "is_" + self.spec.name, checked=checked )
            return checkbox.get_html() + self.get_html_field().get_html()
        else:
            return self.get_html_field().get_html()

    @classmethod
    def unwrap( cls, form_value ):
        value = cls.marshal(form_value)
        cls.validate(value)
        return value
    
class MetadataElementSpec( object ):
    '''
    Defines a metadata element and adds it to the metadata_spec (which
    is a MetadataSpecCollection) of datatype.
    '''

    def __init__( self, datatype, name=None, desc=None, param=MetadataParameter, default=None, no_value = None, **kwargs ):
        self.name = name
        self.desc = desc or name
        self.param = param
        self.default = default
        self.no_value = no_value
        # Catch-all, allows for extra attributes to be set
        self.__dict__.update(kwargs)
        datatype.metadata_spec.append( self )
    def get( self, name ):
        return self.__dict__.get(name, None)
    def hasAttribute( self, attribute ):
        return ((self.permission & attribute) == attribute)
    def wrap( self, value, context ):
        return self.param( self, value, context )
    def unwrap( self, form_value, context ):
        return self.param.unwrap( form_value )
            

# Basic attributes for describing metadata elements
MetadataAttributes = Bunch(
    READONLY = 1, 
    OPTIONAL = 2
    )
    

class MetadataCollection:
    """
    MetadataCollection is not a collection at all, but rather a proxy
    to the real metadata which is stored as a Bunch.  This class
    handles updating the reference to the Bunch when it is changed (so
    that SQLAlchemy knows to update it) as well as returning default
    values in cases when metadata is not set.
    """
    def __init__(self, parent, spec):
        self.parent = parent
        self.bunch = parent._metadata or dict()
        if spec is None: self.spec = MetadataSpecCollection()
        else: self.spec = spec
    def __iter__(self):
        return self.bunch.__iter__()
    def get( self, key, default=None ):
        try:
            return self.bunch.get( key, default ) or self.spec[key].default
        except:
            return default
    def items(self):
        return iter( [(k, self.get(k)) for k in self.spec.iterkeys() ] )
    def __str__(self):
        return dict( self.items() ).__str__()
    def __nonzero__(self):
        return self.bunch.__nonzero__()
    def __getattr__(self, name):
        if self.bunch.get( name ):
            return self.bunch.get( name )
        else:
            if self.spec.get(name, None):
                return self.spec[name].default
            else:
                return None
    def __setattr__(self, name, value):
        if name in ["parent","bunch","spec"]:
            self.__dict__[name] = value
        else:
            self.__dict__["bunch"][name] = value
            self.bunch = self.parent._metadata = dict( self.bunch )

MetadataElement = Statement(MetadataElementSpec)


"""
MetadataParameter sub-classes.
"""

class SelectParameter( MetadataParameter ):
    def __init__( self, spec, value, context ):
        MetadataParameter.__init__( self, spec, value, context )
        self.values = spec.get("values")
    
    def __setattr__(self, name, value):
        MetadataParameter.__setattr__(self, name, value)
        if name in ['value']:
            if value is None: 
                MetadataParameter.__setattr__(self, name, [])
            elif not isinstance(value, list):
                MetadataParameter.__setattr__(self, name, [value])
    
    def __str__(self):
        if self.value in [None, []]:
            return str(self.spec.no_value)
        return ",".join(map(str,self.value))
    
    def get_html_field( self, value=None, other_values={} ):
        field = form_builder.SelectField( self.spec.name, multiple=self.spec.get("multiple"), display=self.spec.get("display") )
        for value, label in self.values or [(value, value) for value in self.value]:
            try:
                if value in self.value:
                    field.add_option( label, value, selected=True )
                else:
                    field.add_option( label, value, selected=False )
            except TypeError:
                field.add_option( value, label, selected=False )

        return field

    def get_html( self ):
        if self.spec.get("readonly"):
            if self.value in [None, [] ]:
                return str(self.spec.no_value)
            return ", ".join(map(str,self.value))
        return MetadataParameter.get_html(self)

    @classmethod
    def marshal( cls, value ):
        # Store select as list, even if single item
        if value is None: return []
        if not isinstance(value, list): return [value]
        return value
    
class RangeParameter( SelectParameter ):
    def __init__( self, spec, value, context ):
        SelectParameter.__init__( self, spec, value, context )
        # The spec must be set with min and max values
        _min = spec.get("min") or 1
        _max = spec.get("max") or 1
        step = self.spec.get("step") or 1
        self.values = zip(range( _min, _max, step ), range( _min, _max, step ))

    @classmethod
    def marshal( cls, value ):
        values = [int(x) for x in value]
        return values
    
class ColumnParameter( RangeParameter ):
    def __init__( self, spec, value, context ):
        RangeParameter.__init__( self, spec, value, context )
        column_range = range( 1, context.metadata.columns+1, 1 )
        self.values = zip( column_range, column_range )
        
    @classmethod
    def marshal( cls, value ):
        return int(value)

