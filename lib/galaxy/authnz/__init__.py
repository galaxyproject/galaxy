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

log = logging.getLogger(__name__)


class IdentityProvider(object):
    """
    OpenID Connect Identity Provider abstract interface.
    """

    def __init__(self, config):
        """
        Initialize the identity provider using the provided configuration,
        and raise a ParseError (or any more related specific exception) in
        case the configuration is malformed.

        :type config: xml.etree.ElementTree.Element
        :param config: Is the configuration element of the provider
            from the configuration file (e.g., OAuth2_config.xml).
            This element contains the all the provider-specific
            configuration elements.
        """
        raise NotImplementedError()

    def authenticate(self, trans):
        """Runs for authentication process. Checks the database if a
        valid identity exists in the database; if yes, then the  user
        is authenticated, if not, it generates a provider-specific
        authentication flow and returns redirect URI to the controller.

        :type trans: GalaxyWebTransaction
        :param trans: Galaxy web transaction.

        :return: a redirect URI to the provider's authentication
            endpoint.
        """
        raise NotImplementedError()

    def callback(self, state_token, authz_code, trans):
        """
        Handles authentication call-backs from identity providers.
        This process maps `state-token` to a user
        :type state_token: string
        :param state_token: is an anti-forgery token which identifies
            a Galaxy user to whom the given authorization code belongs to.
        :type authz_code: string
        :param authz_code: a very short-lived, single-use token to
            request a refresh token.
        :type trans: GalaxyWebTransaction
        :param trans: Galaxy web transaction.
        :return boolean:
            True: if callback is handled successfully.
            False: if processing callback fails, then Galaxy attempts re-authentication.
        """
        raise NotImplementedError()


class AuthnzManager(object):

    def __init__(self, config):
        """
        :type config: string
        :param config: sets the path for OAuth2.0 configuration
            file (e.g., OAuth2_config.xml).
        """
        self._parse_config(config)

    def _parse_config(self, config):
        self.providers = {}
        try:
            tree = ET.parse(config)
            root = tree.getroot()
            if root.tag != 'OAuth2.0':
                raise ParseError("The root element in OAuth2.0 config xml file is expected to be `OAuth2.0`, "
                                 "found `{}` instead -- unable to continue.".format(root.tag))
            for child in root:
                if child.tag != 'provider':
                    log.error("Expect a node with `provider` tag, found a node with `{}` tag instead; "
                              "skipping the node.".format(child.tag))
                    continue
                if 'name' not in child.attrib:
                    log.error("Could not find a node attribute 'name'; skipping the node '{}'.".format(child.tag))
                    continue
                provider = child.get('name')
                try:
                    if provider == 'Google':
                        from .oidc_idp_google import OIDCIdPGoogle
                        self.providers[provider] = OIDCIdPGoogle(child)
                except ParseError:
                    log.error("Could not initialize `{}` identity provider; skipping this node.".format(provider))
                    continue
            if len(self.providers) == 0:
                raise ParseError("No valid provider configuration parsed.")
        except ImportError:
            raise
        except ParseError as e:
            raise ParseError("Invalid configuration at `{}`: {} -- unable to continue.".format(config, e.message))
        except Exception:
            raise ParseError("Malformed OAuth2.0 Configuration XML -- unable to continue.")

    def authenticate(self, provider, trans):
        """
        :type provider: string
        :param provider: set the name of the identity provider to be
            used for authentication flow.
        :type trans: GalaxyWebTransaction
        :param trans: Galaxy web transaction.
        :return: an identity provider specific authentication redirect URI.
        """
        if provider in self.providers:
            try:
                return self.providers[ provider ].authenticate( trans )
            except:
                raise
        else:
            log.error("The provider '{}' is not a recognized and expected provider.".format(provider))

    def callback(self, provider, state_token, authz_code, trans):
        if provider in self.providers:
            try:
                return self.providers[provider].callback(state_token, authz_code, trans)
            except:
                raise
        else:
            raise NameError("The provider '{}' is not a recognized and expected provider.".format(provider))
