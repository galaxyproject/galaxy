import urllib2
import sys, logging
from galaxy.util import parse_xml
from galaxy.util.odict import odict

log = logging.getLogger( __name__ )

from xml.etree import ElementTree

class Registry( object ):
    def __init__( self, root_dir=None, config=None ):
        self.tool_sheds      = odict()
        self.tool_sheds_auth = odict()
        if root_dir and config:
            # Parse tool_sheds_conf.xml
            tree = parse_xml( config )
            root = tree.getroot()
            log.debug( 'Loading references to tool sheds from %s' % config )
            for elem in root.findall( 'tool_shed' ):
                try:
                    name     = elem.get( 'name', None )
                    url      = elem.get( 'url', None )
                    username = elem.get( 'user', None )
                    password = elem.get( 'pass', None )
                    if name and url:
                        self.tool_sheds[ name ]      = url
                        self.tool_sheds_auth[ name ] = None
                        log.debug( 'Loaded reference to tool shed: %s' % name )
                    if name and url and username and password:
                        pass_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
                        pass_mgr.add_password(None, url, username, password)
                        self.tool_sheds_auth[ name ] = pass_mgr
                except Exception, e:
                    log.warning( 'Error loading reference to tool shed "%s", problem: %s' % ( name, str( e ) ) )

    def url_from_tool_shed( self, tool_shed ):
        """
        The value of tool_shed is something like: toolshed.g2.bx.psu.edu
        We need the URL to this tool shed, which is something like:
        http://toolshed.g2.bx.psu.edu/
        """
        for shed_name, shed_url in self.tool_sheds.items():
            if shed_url.find( tool_shed ) >= 0:
                if shed_url.endswith( '/' ):
                    shed_url = shed_url.rstrip( '/' )
                return shed_url
        # The tool shed from which the repository was originally installed 
        # must no longer be configured in tool_sheds_conf.xml.
        return None

    def password_manager_for_url(self, url):
        """
        If the tool shed is using external auth, the client to the toolshed must
        authenticate to that as well.  This provides access to the 
        urllib2.HTTPPasswordMgrWithdefaultRealm() object for the url passed in.

        Following more what galaxy.demo_sequencer.controllers.common does might
        be more appropriate at some stage...
        """
        log.debug( 'Looking for url %s' % url )
        
        for shed_name, shed_url in self.tool_sheds.items():
            if shed_url.find( url ) >= 0:
                log.debug( 'Found %s -> %s' % (shed_name, shed_url) )
                return self.tool_sheds_auth[ shed_name ]
        return None
