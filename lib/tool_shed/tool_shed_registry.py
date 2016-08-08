import logging

from six.moves.urllib import request as urlrequest

from galaxy.util.odict import odict
from tool_shed.util import common_util, xml_util

log = logging.getLogger( __name__ )


class Registry( object ):

    def __init__( self, root_dir=None, config=None ):
        self.tool_sheds = odict()
        self.tool_sheds_auth = odict()
        if root_dir and config:
            # Parse tool_sheds_conf.xml
            tree, error_message = xml_util.parse_xml( config )
            if tree is None:
                log.warning( "Unable to load references to tool sheds defined in file %s" % str( config ) )
            else:
                root = tree.getroot()
                log.debug( 'Loading references to tool sheds from %s' % config )
                for elem in root.findall( 'tool_shed' ):
                    try:
                        name = elem.get( 'name', None )
                        url = elem.get( 'url', None )
                        username = elem.get( 'user', None )
                        password = elem.get( 'pass', None )
                        if name and url:
                            self.tool_sheds[ name ] = url
                            self.tool_sheds_auth[ name ] = None
                            log.debug( 'Loaded reference to tool shed: %s' % name )
                        if name and url and username and password:
                            pass_mgr = urlrequest.HTTPPasswordMgrWithDefaultRealm()
                            pass_mgr.add_password( None, url, username, password )
                            self.tool_sheds_auth[ name ] = pass_mgr
                    except Exception as e:
                        log.warning( 'Error loading reference to tool shed "%s", problem: %s' % ( name, str( e ) ) )

    def password_manager_for_url( self, url ):
        """
        If the tool shed is using external auth, the client to the tool shed must authenticate to that
        as well.  This provides access to the six.moves.urllib.request.HTTPPasswordMgrWithdefaultRealm() object for the
        url passed in.

        Following more what galaxy.demo_sequencer.controllers.common does might be more appropriate at
        some stage...
        """
        url_sans_protocol = common_util.remove_protocol_from_tool_shed_url( url )
        for shed_name, shed_url in self.tool_sheds.items():
            shed_url_sans_protocol = common_util.remove_protocol_from_tool_shed_url( shed_url )
            if url_sans_protocol.startswith( shed_url_sans_protocol ):
                return self.tool_sheds_auth[ shed_name ]
        log.debug( "Invalid url '%s' received by tool shed registry's password_manager_for_url method." % str( url ) )
        return None

    def url_auth( self, url ):
        password_manager = self.password_manager_for_url( url )
        if password_manager is not None:
            return urlrequest.HTTPBasicAuthHandler( password_manager )
