import sys, logging
from galaxy.util import parse_xml
from galaxy.util.odict import odict

log = logging.getLogger( __name__ )

if sys.version_info[:2] == ( 2, 4 ):
    from galaxy import eggs
    eggs.require( 'ElementTree' )
    from elementtree import ElementTree
else:
    from xml.etree import ElementTree

class Registry( object ):
    def __init__( self, root_dir=None, config=None ):
        self.tool_sheds = odict()
        if root_dir and config:
            # Parse datatypes_conf.xml
            tree = parse_xml( config )
            root = tree.getroot()
            # Load datatypes and converters from config
            log.debug( 'Loading references to tool sheds from %s' % config )
            for elem in root.findall( 'tool_shed' ):
                try:
                    name = elem.get( 'name', None )
                    url = elem.get( 'url', None )
                    if name and url:
                        self.tool_sheds[ name ] = url
                        log.debug( 'Loaded reference to tool shed: %s' % name )
                except Exception, e:
                    log.warning( 'Error loading reference to tool shed "%s", problem: %s' % ( name, str( e ) ) )
