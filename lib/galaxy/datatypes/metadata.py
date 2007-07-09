import sys
from cookbook.patterns import Bunch

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

class MetadataSpecCollection( dict ):
    '''
    A simple extension of dict which allows cleaner access to items
    and allows the values to be iterated over directly as if it were a
    list.  append() is also implemented for simplicity and does not
    "append".
    '''
    def append( self, item ):
        self[item.name] = item
    def iter( self ):
        return self.itervalues()
    def __getattr__( self, name ):
        return self[name]

class MetadataParameter( object ):
    def __init__( self, metadata, context ):
        '''
        The "context" is simply the metadata collection/bunch holding
        this piece of metadata.  This is passed in to allow for
        metadata to validate against each other (note: this could turn
        into a huge, recursive mess if not done with care).  For
        example, a column assignment should validate against the
        number of columns in the dataset.
        '''
        self.metadata = metadata
        self.context = context
    def marshal( self, value ):
        '''
        This method should/can be overridden to convert the incomming
        value to whatever type it is supposed to be.
        '''
        return value

    def validate( self, value ):
        '''
        Throw an exception if the value is invalid.
        '''
        pass

    def get_html_field( self, value=None, other_values={} ):
        raise TypeError("Abstract Method")
    
    @classmethod
    def build_param( cls, element, context ):
        return element.param( element, context )


class MetadataElementSpec( object ):
    '''
    Defines a metadata element and adds it to the metadata_spec (which
    is a MetadataSpecCollection) of datatype.
    '''

    def __init__( self, datatype, name=None, desc=None, param=MetadataParameter, attributes=None, default=None ):
        self.name = name
        self.desc = desc
        self.param = param
        self.attributes = attributes
        self.default = default
        datatype.metadata_spec.append( self )
    def hasAttribute( self, attribute ):
        return ((self.permission & attribute) == attribute)
    def wrap( self, metadata ):
        return self.param(metadata)


# Basic attributes for describing metadata elements
MetadataAttributes = Bunch(
    READONLY = 1
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
        self.bunch = parent._metadata or Bunch()
        self.spec = spec or dict()
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
            setattr(self.__dict__["bunch"], name, value)
            self.bunch = self.parent._metadata = Bunch( **self.bunch.__dict__ )

MetadataElement = Statement(MetadataElementSpec)


