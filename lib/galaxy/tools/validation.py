"""
Classes related to parameter validation.
"""

import re, logging
from elementtree.ElementTree import XML

log = logging.getLogger( __name__ )

class Validator( object ):
    """
    A validator checks that a value meets some conditions OR raises ValueError
    """
    @classmethod
    def from_element( cls, elem ):
        type = elem.get( 'type' )
        return validator_types[type].from_element( elem )
    def validate( self, value, history=None ):
        raise TypeError( "Abstract Method" )
        
class RegexValidator( Validator ):
    """
    Validator that evaluates a regular expression
    
    >>> from galaxy.tools.parameters import ToolParameter
    >>> p = ToolParameter.build( None, XML( '''
    ... <param name="blah" type="text" size="10" value="10">
    ...     <validator type="regex" message="Not gonna happen">[Ff]oo</validator>
    ... </param>
    ... ''' ) )
    >>> t = p.validate( "Foo" )
    >>> t = p.validate( "foo" )
    >>> t = p.validate( "Fop" )
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    """
    @classmethod
    def from_element( cls, elem ):
        return cls( elem.get( 'message' ), elem.text )
    def __init__( self, message, expression ):
        self.message = message
        # Compile later. RE objects used to not be thread safe. Not sure about
        # the sre module. 
        self.expression = expression  
    def validate( self, value, history=None ):
        if re.match( self.expression, value ) is None:
            raise ValueError( self.message )
        
class ExpressionValidator( Validator ):
    """
    Validator that evaluates a python expression using the value
    
    >>> from galaxy.tools.parameters import ToolParameter
    >>> p = ToolParameter.build( None, XML( '''
    ... <param name="blah" type="text" size="10" value="10">
    ...     <validator type="expression" message="Not gonna happen">value.lower() == "foo"</validator>
    ... </param>
    ... ''' ) )
    >>> t = p.validate( "Foo" )
    >>> t = p.validate( "foo" )
    >>> t = p.validate( "Fop" )
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    """
    @classmethod
    def from_element( cls, elem ):
        return cls( elem.get( 'message' ), elem.text )
    def __init__( self, message, expression ):
        self.message = message
        # Save compiled expression, code objects are thread safe (right?)
        self.expression = compile( expression, '<string>', 'eval' )    
    def validate( self, value, history=None ):
        if not( eval( self.expression, dict( value=value ) ) ):
            raise ValueError( self.message )
        
class InRangeValidator( Validator ):
    """
    Validator that ensures a number is in a specific range
    
    >>> from galaxy.tools.parameters import ToolParameter
    >>> p = ToolParameter.build( None, XML( '''
    ... <param name="blah" type="integer" size="10" value="10">
    ...     <validator type="in_range" message="Not gonna happen" min="10" max="20"/>
    ... </param>
    ... ''' ) )
    >>> t = p.validate( 10 )
    >>> t = p.validate( 15 )
    >>> t = p.validate( 20 )
    >>> t = p.validate( 21 )
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    """
    @classmethod
    def from_element( cls, elem ):
        return cls( elem.get( 'message', None ), elem.get( 'min' ), elem.get( 'max' ) )
    def __init__( self, message, min, max ):
        self.message = message or ( "Value must be between %f and %f" % ( min, max ) )
        self.min = float( min )
        self.max = float( max )    
    def validate( self, value, history=None ):
        if not( self.min <= float( value ) <= self.max ):
            raise ValueError( self.message )   
        
class LengthValidator( Validator ):
    """
    Validator that ensures a number is in a specific range

    >>> from galaxy.tools.parameters import ToolParameter
    >>> p = ToolParameter.build( None, XML( '''
    ... <param name="blah" type="text" size="10" value="foobar">
    ...     <validator type="length" min="2" max="8"/>
    ... </param>
    ... ''' ) )
    >>> t = p.validate( "foo" )
    >>> t = p.validate( "bar" )
    >>> t = p.validate( "f" )
    Traceback (most recent call last):
        ...
    ValueError: Must have length of at least 2
    >>> t = p.validate( "foobarbaz" )
    Traceback (most recent call last):
        ...
    ValueError: Must have length no more than 8
    """
    @classmethod
    def from_element( cls, elem ):
        return cls( elem.get( 'message', None ), elem.get( 'min', None ), elem.get( 'max', None ) )
    def __init__( self, message, min, max ):
        self.message = message
        if min is not None: 
            min = int( min )
        if max is not None:
            max = int( max )
        self.min = min
        self.max = max
    def validate( self, value, history=None ):
        if self.min is not None and len( value ) < self.min:
            raise ValueError( self.message or ( "Must have length of at least %d" % self.min ) )
        if self.max is not None and len( value ) > self.max:
            raise ValueError( self.message or ( "Must have length no more than %d" % self.max ) )

class MetadataValidator( Validator ):
    """
    Validator that checks for missing metadata
    """
    def validate( self, value, history=None ):
        if value.missing_meta():
            raise ValueError( "Metadata missing, click the pencil icon in the history item to edit / save the metadata attributes" )

validator_types = dict( expression=ExpressionValidator,
                        regex=RegexValidator,
                        in_range=InRangeValidator,
                        length=LengthValidator,
                        metadata=MetadataValidator )
                        
def get_suite():
    """Get unittest suite for this module"""
    import doctest, sys
    return doctest.DocTestSuite( sys.modules[__name__] )