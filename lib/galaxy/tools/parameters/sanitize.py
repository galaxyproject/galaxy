"""
Tool Parameter specific sanitizing. 
"""

import logging
import string
import galaxy.util

log = logging.getLogger( __name__ )

class ToolParameterSanitizer( object ):
    """
    Handles tool parameter specific sanitizing.
    
    >>> from elementtree.ElementTree import XML
    >>> sanitizer = ToolParameterSanitizer.from_element( XML( 
    ... '''
    ... <sanitizer invalid_char="">
    ...   <valid initial="string.letters"/>
    ... </sanitizer>
    ... ''' ) )
    >>> sanitizer.sanitize_param( ''.join( sorted( [ c for c in string.printable ] ) ) ) == ''.join( sorted( [ c for c in string.letters ] ) )
    True
    >>> slash = chr( 92 )
    >>> sanitizer = ToolParameterSanitizer.from_element( XML( 
    ... '''
    ... <sanitizer>
    ...   <valid initial="none">
    ...    <add preset="string.printable"/>
    ...    <remove value="&quot;"/>
    ...    <remove value="%s"/>
    ...   </valid>
    ...   <mapping initial="none">
    ...     <add source="&quot;" target="%s&quot;"/>
    ...     <add source="%s" target="%s%s"/>
    ...   </mapping>
    ... </sanitizer>
    ... ''' % ( slash, slash, slash, slash, slash ) ) )
    >>> text = '%s"$rm&#!' % slash
    >>> [ c for c in sanitizer.sanitize_param( text ) ] == [ slash, slash, slash, '"', '$', 'r', 'm', '&', '#', '!' ]
    True
    """
    
    VALID_PRESET = { 'default':( string.letters + string.digits +" -=_.()/+*^,:?!" ), 'none':'' }
    MAPPING_PRESET = { 'default':galaxy.util.mapped_chars, 'none':{} }
    DEFAULT_INVALID_CHAR = 'X'
    
    #class methods
    @classmethod
    def from_element( cls, elem ):
        """Loads the proper filter by the type attribute of elem"""
        #TODO: Add ability to generically specify a method to use for sanitizing input via specification in tool XML
        rval = ToolParameterSanitizer()
        rval._invalid_char = elem.get( 'invalid_char', cls.DEFAULT_INVALID_CHAR )
        rval.sanitize = galaxy.util.string_as_bool( elem.get( 'sanitize', 'True' ) )
        for valid_elem in elem.findall( 'valid' ):
            rval._valid_chars = rval.get_valid_by_name( valid_elem.get( 'initial', 'default' ) )
            for action_elem in valid_elem:
                preset = rval.get_valid_by_name( action_elem.get( 'preset', 'none' ) )
                valid_value = [ val for val in action_elem.get( 'value', [] ) ]
                if action_elem.tag.lower() == 'add':
                    for val in ( preset + valid_value ):
                        if val not in rval._valid_chars:
                            rval._valid_chars.append( val )
                elif action_elem.tag.lower() == 'remove':
                    for val in ( preset + valid_value ):
                        while val in rval._valid_chars:
                            rval._valid_chars.remove( val )
                else:
                    log.debug( 'Invalid action tag in valid: %s' % action_elem.tag )
        for mapping_elem in elem.findall( 'mapping' ):
            rval._mapped_chars = rval.get_mapping_by_name( mapping_elem.get( 'initial', 'default' ) )
            for action_elem in mapping_elem:
                map_source = action_elem.get( 'source', None )
                map_target = action_elem.get( 'target', None )
                preset = rval.get_mapping_by_name( action_elem.get( 'preset', 'none' ) )
                if action_elem.tag.lower() == 'add':
                    rval._mapped_chars.update( preset )
                    if None not in [ map_source, map_target ]:
                        rval._mapped_chars[ map_source ] = map_target
                elif action_elem.tag.lower() == 'remove':
                    for map_key in preset.keys():
                        if map_key in rval._mapped_chars:
                            del rval._mapped_chars[ map_key ]
                    if map_source is not None and map_key in rval._mapped_chars:
                        del rval._mapped_chars[ map_key ]
                else:
                    log.debug( 'Invalid action tag in mapping: %s' % action_elem.tag )        
        return rval
    
    @classmethod
    def get_valid_by_name( cls, name ):
        rval = []
        for split_name in name.split( ',' ):
            split_name = split_name.strip()
            value = []
            if split_name.startswith( 'string.' ):
                try:
                    value = eval( split_name )
                except NameError, e:
                    log.debug( 'Invalid string preset specified: %s' % e )
            elif split_name in cls.VALID_PRESET:
                value = cls.VALID_PRESET[ split_name ]
            else:
                log.debug( 'Invalid preset name specified: %s' % split_name )
            rval.extend( [ val for val in value if val not in rval ] )
        return rval
    
    @classmethod
    def get_mapping_by_name( cls, name ):
        rval = {}
        for split_name in name.split( ',' ):
            split_name = split_name.strip()
            if split_name in cls.MAPPING_PRESET:
                rval.update( cls.MAPPING_PRESET[ split_name ] )
            else:
                log.debug( 'Invalid preset name specified: %s' % split_name )
        return rval
    #end class methods
    
    def __init__( self ):
        self._valid_chars = [] #List of valid characters
        self._mapped_chars = {} #Replace a char with a any number of characters
        self._invalid_char = self.DEFAULT_INVALID_CHAR #Replace invalid characters with this character
        self.sanitize = True #Simply pass back the passed in value
    
    def restore_text( self, text ):
        """Restores sanitized text"""
        if self.sanitize:
            for key, value in self._mapped_chars.iteritems():
                text = text.replace( value, key )
        return text
    
    def restore_param( self, value ):
        if self.sanitize:
            if isinstance( value, basestring ):
                return self.restore_text( value )
            elif isinstance( value, list ):
                return map( self.restore_text, value )
            else:
                raise Exception, 'Unknown parameter type (%s:%s)' % ( type( value ), value )
        return value
    
    def sanitize_text( self, text ):
        """Restricts the characters that are allowed in a text"""
        if not self.sanitize:
            return text
        rval = []
        for c in text:
            if c in self._valid_chars:
                rval.append( c )
            elif c in self._mapped_chars:
                rval.append( self._mapped_chars[ c ] )
            else:
                rval.append( self._invalid_char )
        return ''.join( rval )
    
    def sanitize_param( self, value ):
        """Clean incoming parameters (strings or lists)"""
        if not self.sanitize:
            return value
        if isinstance( value, basestring ):
            return self.sanitize_text( value )
        elif isinstance( value, list ):
            return map( self.sanitize_text, value )
        else:
            raise Exception, 'Unknown parameter type (%s:%s)' % ( type( value ), value )
