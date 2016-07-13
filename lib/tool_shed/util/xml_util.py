import logging
import sys
import tempfile
import xml.etree.ElementTree
from xml.etree import ElementTree as XmlET

from galaxy.util import listify

log = logging.getLogger( __name__ )
using_python_27 = sys.version_info[ :2 ] >= ( 2, 7 )


class Py26CommentedTreeBuilder( XmlET.XMLTreeBuilder ):
    # Python 2.6 uses ElementTree 1.2.x.

    def __init__( self, html=0, target=None ):
        XmlET.XMLTreeBuilder.__init__( self, html, target )
        self._parser.CommentHandler = self.handle_comment

    def handle_comment( self, data ):
        self._target.start( XmlET.Comment, {} )
        self._target.data( data )
        self._target.end( XmlET.Comment )


class Py27CommentedTreeBuilder( XmlET.TreeBuilder ):
    # Python 2.7 uses ElementTree 1.3.x.

    def comment( self, data ):
        self.start( XmlET.Comment, {} )
        self.data( data )
        self.end( XmlET.Comment )


def create_and_write_tmp_file( elems, use_indent=False ):
    tmp_str = ''
    for elem in listify( elems ):
        tmp_str += xml_to_string( elem, use_indent=use_indent )
    fh = tempfile.NamedTemporaryFile( 'wb', prefix="tmp-toolshed-cawrf"  )
    tmp_filename = fh.name
    fh.close()
    fh = open( tmp_filename, 'wb' )
    fh.write( '<?xml version="1.0"?>\n' )
    fh.write( tmp_str )
    fh.close()
    return tmp_filename


def create_element( tag, attributes=None, sub_elements=None ):
    """
    Create a new element whose tag is the value of the received tag, and whose attributes are all
    key / value pairs in the received attributes and sub_elements.
    """
    if tag:
        elem = XmlET.Element( tag )
        if attributes:
            # The received attributes is an odict to preserve ordering.
            for k, v in attributes.items():
                elem.set( k, v )
        if sub_elements:
            # The received attributes is an odict.  These handle information that tends to be
            # long text including paragraphs (e.g., description and long_description.
            for k, v in sub_elements.items():
                # Don't include fields that are blank.
                if v:
                    if k == 'packages':
                        # The received sub_elements is an odict whose key is 'packages' and whose
                        # value is a list of ( name, version ) tuples.
                        for v_tuple in v:
                            sub_elem = XmlET.SubElement( elem, 'package' )
                            sub_elem_name, sub_elem_version = v_tuple
                            sub_elem.set( 'name', sub_elem_name )
                            sub_elem.set( 'version', sub_elem_version )
                    elif isinstance( v, list ):
                        sub_elem = XmlET.SubElement( elem, k )
                        # If v is a list, then it must be a list of tuples where the first
                        # item is the tag and the second item is the text value.
                        for v_tuple in v:
                            if len( v_tuple ) == 2:
                                v_tag = v_tuple[ 0 ]
                                v_text = v_tuple[ 1 ]
                                # Don't include fields that are blank.
                                if v_text:
                                    v_elem = XmlET.SubElement( sub_elem, v_tag )
                                    v_elem.text = v_text
                    else:
                        sub_elem = XmlET.SubElement( elem, k )
                        sub_elem.text = v
        return elem
    return None


def indent( elem, level=0 ):
    """
    Prints an XML tree with each node indented according to its depth.  This method is used to print the
    shed tool config (e.g., shed_tool_conf.xml from the in-memory list of config_elems because each config_elem
    in the list may be a hierarchical structure that was not created using the parse_xml() method below,
    and so will not be properly written with xml.etree.ElementTree.tostring() without manually indenting
    the tree first.
    """
    i = "\n" + level * "    "
    if len( elem ):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            indent( child, level + 1 )
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
        except Exception as e:
            fobj.close()
            error_message = "Exception attempting to parse %s: %s" % ( str( file_name ), str( e ) )
            log.exception( error_message )
            return None, error_message
    else:
        try:
            tree = XmlET.parse( fobj, parser=Py26CommentedTreeBuilder() )
        except Exception as e:
            fobj.close()
            error_message = "Exception attempting to parse %s: %s" % ( str( file_name ), str( e ) )
            log.exception( error_message )
            return None, error_message
    fobj.close()
    return tree, error_message


def xml_to_string( elem, encoding='utf-8', use_indent=False, level=0 ):
    if elem is not None:
        if use_indent:
            # We were called from ToolPanelManager.config_elems_to_xml_file(), so
            # set the level to 1 since level 0 is the <toolbox> tag set.
            indent( elem, level=level )
        if using_python_27:
            xml_str = '%s\n' % xml.etree.ElementTree.tostring( elem, encoding=encoding, method="xml" )
        else:
            xml_str = '%s\n' % xml.etree.ElementTree.tostring( elem, encoding=encoding )
    else:
        xml_str = ''
    return xml_str
