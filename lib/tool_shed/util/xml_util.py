import logging
import os
import sys
import tempfile
from xml.etree import ElementTree as XmlET
import xml.etree.ElementTree

log = logging.getLogger( __name__ )
using_python_27 = sys.version_info[ :2 ] >= ( 2, 7 )


class Py26CommentedTreeBuilder ( XmlET.XMLTreeBuilder ):
    # Python 2.6 uses ElementTree 1.2.x.

    def __init__ ( self, html=0, target=None ):
        XmlET.XMLTreeBuilder.__init__( self, html, target )
        self._parser.CommentHandler = self.handle_comment
    
    def handle_comment ( self, data ):
        self._target.start( XmlET.Comment, {} )
        self._target.data( data )
        self._target.end( XmlET.Comment )


class Py27CommentedTreeBuilder ( XmlET.TreeBuilder ):
    # Python 2.7 uses ElementTree 1.3.x.
    
    def comment( self, data ):
        self.start( XmlET.Comment, {} )
        self.data( data )
        self.end( XmlET.Comment )

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
    error_message = ''
    fobj = open( file_name, 'r' )
    if using_python_27:
        try:
            tree = XmlET.parse( fobj, parser=XmlET.XMLParser( target=Py27CommentedTreeBuilder() ) )
        except Exception, e:
            fobj.close()
            error_message = "Exception attempting to parse %s: %s" % ( str( file_name ), str( e ) )
            log.exception( error_message )
            return None, error_message
    else:
        try:
            tree = XmlET.parse( fobj, parser=Py26CommentedTreeBuilder() )
        except Exception, e:
            fobj.close()
            error_message = "Exception attempting to parse %s: %s" % ( str( file_name ), str( e ) )
            log.exception( error_message )
            return None, error_message
    fobj.close()
    return tree, error_message

def xml_to_string( elem, encoding='utf-8' ):
    if using_python_27:
        xml_str = '%s\n' % xml.etree.ElementTree.tostring( elem, encoding=encoding, method="xml" )
    else:
        xml_str = '%s\n' % xml.etree.ElementTree.tostring( elem, encoding=encoding )
    return xml_str
