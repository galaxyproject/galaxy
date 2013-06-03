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

def indent( elem, level=0 ):
    """
    Prints an XML tree with each node indented according to its depth.  This method is used to print the shed tool config (e.g., shed_tool_conf.xml
    from the in-memory list of config_elems because each config_elem in the list may be a hierarchical structure that was not created using the
    parse_xml() method below, and so will not be properly written with xml.etree.ElementTree.tostring() without manually indenting the tree first.
    """
    i = "\n" + level * "    "
    if len( elem ):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            indent( child, level+1 )
        if not child.tail or not child.tail.strip():
            child.tail = i
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and ( not elem.tail or not elem.tail.strip() ):
            elem.tail = i

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

def xml_to_string( elem, encoding='utf-8', use_indent=False ):
    if elem:
        if use_indent:
            # We were called from suc.config_elems_to_xml_file(), so set the level to 1 since level 0 is the <toolbox> tag set.
            indent( elem, level=1 )
        if using_python_27:
            xml_str = '%s\n' % xml.etree.ElementTree.tostring( elem, encoding=encoding, method="xml" )
        else:
            xml_str = '%s\n' % xml.etree.ElementTree.tostring( elem, encoding=encoding )
    else:
        xml_str = ''
    return xml_str
