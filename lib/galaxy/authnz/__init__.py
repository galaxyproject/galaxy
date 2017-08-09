"""
Contains implementations for authentication and authorization against third-party
OAuth2.0 authorization servers and OpenID Connect Identity providers.

This package follows "authorization code flow" authentication protocol to authenticate
Galaxy users against third-party identity providers.

Additionally, this package implements functionalist's to request temporary access
credentials for cloud-based resource providers (e.g., Amazon AWS, Microsoft Azure).
"""

import logging
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError

log = logging.getLogger( __name__ )

class AuthnzManager( object ):

    def __init__( self, config ):
        self._parse_config( config )
        return

    def _parse_config( self, config ):
        self.providers = {}
        try:
            tree = ET.parse( config )
            root = tree.getroot()
            if root.tag != 'OAuth2.0':
                raise ParseError( "The root element in OAuth2.0 config xml file is expected to be `OAuth2.0`, "
                                  "found `{}` instead -- unable to continue.".format( root.tag ) )
            for child in root:
                if child.tag != 'provider':
                    log.error( "Expect a node with `provider` tag, found a node with `{}` tag instead; "
                               "skipping the node.".format( child.tag ) )
                    continue
                if 'name' not in child.attrib:
                    log.error( "Could not find a node attribute 'name'; skipping the node '{}'.".format( child.tag ) )
                    continue
                client_secret_file = child.find('client_secret_file')
                if client_secret_file is None:
                    log.error( "Did not find `client_secret_file` key in the configuration; skipping the node '{}'."
                               .format( child.tag ) )
                    continue
                redirect_uri = child.find( 'redirect_uri' )
                if redirect_uri is None:
                    log.error( "Did not find `redirect_uri` key in the configuration; skipping the node '{}'."
                               .format( child.tag ) )
                    continue
                self.providers[child.get( 'name' )] = { 'client_secret_file': client_secret_file.text,
                                                        'redirect_uri': redirect_uri.text }
            if len( self.providers ) == 0:
                raise ParseError( "No valid provider configuration parsed." )
        except Exception:
            log.exception("Malformed OAuth2.0 Configuration XML -- unable to continue.")
            raise
