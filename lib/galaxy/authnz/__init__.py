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
                raise ParseError( "The root element in OAuth2.0 config xml file is expected to be `OAuth2.0`, found `{}` instead -- unable to continue.".format( root.tag ) )
            for child in root:
                if child.tag != 'provider':
                    raise ParseError( "Expect a node with `provider` tag, found a node with `{}` tag instead -- unable to continue.".format( child.tag ) )
                if 'name' not in child.attrib:
                    raise ParseError( "Could not find a node attribute 'name' -- unable to continue." )
                if 'client_secret_file' not in child.attrib:
                    raise ParseError("Could not find a node attribute 'client_secret_file' -- unable to continue.")
                self.providers[child.get( 'name' )] = child.get( 'client_secret_file' )
        except Exception:
            log.exception("Malformed OAuth2.0 Configuration XML -- unable to continue.")
            raise
