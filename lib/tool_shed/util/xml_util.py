import logging
import os
import tempfile
from xml.etree import ElementTree as XmlET
import xml.etree.ElementTree

log = logging.getLogger( __name__ )


class CommentedTreeBuilder ( XmlET.XMLTreeBuilder ):
    def __init__ ( self, html=0, target=None ):
        XmlET.XMLTreeBuilder.__init__( self, html, target )
        self._parser.CommentHandler = self.handle_comment
    
    def handle_comment ( self, data ):
        self._target.start( XmlET.Comment, {} )
        self._target.data( data )
        self._target.end( XmlET.Comment )

def create_and_write_tmp_file( elem ):
    tmp_str = xml_to_string( elem )
    fh = tempfile.NamedTemporaryFile( 'wb' )
    tmp_filename = fh.name
    fh.close()
    fh = open( tmp_filename, 'wb' )
    fh.write( '<?xml version="1.0"?>\n' )
    fh.write( tmp_str )
    fh.close()
    return tmp_filename

def parse_xml( file_name ):
    """Returns a parsed xml tree with comments intact."""
    try:
        fobj = open( file_name, 'r' )
        tree = XmlET.parse( fobj, parser=CommentedTreeBuilder() )
        fobj.close()
    except Exception, e:
        log.exception( "Exception attempting to parse %s: %s" % ( str( file_name ), str( e ) ) )
        return None
    return tree

def xml_to_string( elem, encoding='utf-8' ):
    return '%s\n' % xml.etree.ElementTree.tostring( elem, encoding=encoding )
