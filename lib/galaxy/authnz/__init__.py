"""
Contains implementations for authentication and authorization against an
OpenID Connect (OIDC) Identity Provider (IdP).

This package follows "authorization code flow" authentication protocol to authenticate
Galaxy users against third-party identity providers.

Additionally, this package implements functionalist's to request temporary access
credentials for cloud-based resource providers (e.g., Amazon AWS, Microsoft Azure).
"""


class IdentityProvider(object):
    """
    OpenID Connect Identity Provider abstract interface.
    """

    def __init__(self, provider, config):
        """
        Initialize the identity provider using the provided configuration,
        and raise a ParseError (or any more related specific exception) in
        case the configuration is malformed.

        :type provider: string
        :param provider: is the name of the identity provider (e.g., Google).

        :type config: xml.etree.ElementTree.Element
        :param config: Is the configuration element of the provider
            from the configuration file (e.g., oidc_config.xml).
            This element contains the all the provider-specific
            configuration elements.
        """
        raise NotImplementedError()

    def authenticate(self, provider, trans):
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

    def callback(self, state_token, authz_code, trans, login_redirect_url):
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

    def disconnect(self, provider, trans, disconnect_redirect_url=None):
        raise NotImplementedError()
