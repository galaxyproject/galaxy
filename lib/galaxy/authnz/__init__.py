"""
Contains implementations for authentication and authorization against an
OpenID Connect (OIDC) Identity Provider (IdP).

This package follows "authorization code flow" authentication protocol to authenticate
Galaxy users against third-party identity providers.

Additionally, this package implements functionalist's to request temporary access
credentials for cloud-based resource providers (e.g., Amazon AWS, Microsoft Azure).
"""


class IdentityProvider:
    """
    OpenID Connect Identity Provider abstract interface.
    """

    def __init__(self, provider, config, backend_config):
        """
        Initialize the identity provider using the provided configuration,
        and raise a ParseError (or any more related specific exception) in
        case the configuration is malformed.

        :type provider: string
        :param provider: is the name of the identity provider (e.g., Google).

        :type config: lxml.etree.ElementTree._Element
        :param config: Is the configuration element of the provider
                       from the configuration file (e.g., oidc_config.xml).
                       This element contains the all the provider-specific
                       configuration elements.

        :type backend_config: lxml.etree.ElementTree._Element
        :param backend_config:

            Is the configuration element of the backend of
            the provider from the configuration file (e.g.,
            oidc_backends_config.xml). This element contains all the
            backend-specific configuration elements.
        """
        raise NotImplementedError()

    def refresh(self, trans, token):
        raise NotImplementedError()

    def authenticate(self, trans, idphint=None):
        """Runs for authentication process. Checks the database if a
        valid identity exists in the database; if yes, then the  user
        is authenticated, if not, it generates a provider-specific
        authentication flow and returns redirect URI to the controller.

        :type trans: GalaxyWebTransaction
        :param trans: Galaxy web transaction.

        :returns: a redirect URI to the provider's authentication endpoint
        """
        raise NotImplementedError()

    def callback(self, state_token: str, authz_code: str, trans, login_redirect_url):
        """Handles authentication call-backs from identity providers.

        This process maps `state-token` to a user.

        :param state_token: is an anti-forgery token which identifies
                            a Galaxy user to whom the given authorization code belongs to.
        :param authz_code: a very short-lived, single-use token to
                           request a refresh token.
        :type trans: GalaxyWebTransaction
        :param trans: Galaxy web transaction.
        :rtype: tuple
        :returns: a tuple of redirect_url and user.
        """
        raise NotImplementedError()

    def disconnect(self, provider, trans, disconnect_redirect_url=None, email=None, association_id=None):
        raise NotImplementedError()

    def logout(self, trans, post_user_logout_href=None):
        """
        Return a URL that will log the user out of the IDP. In OIDC this is
        called the 'end_session_endpoint'.

        :type trans: GalaxyWebTransaction
        :param trans: Galaxy web transaction.

        :type post_user_logout_href: string
        :param post_user_logout_href: Optional URL to redirect to after logging out of IDP.
        """
        raise NotImplementedError()

    def decode_user_access_token(self, sa_session, access_token):
        """
        Verifies and decodes an access token against this provider, returning the user and
        a dict containing the decoded token data.

        :type  sa_session:      sqlalchemy.orm.scoping.scoped_session
        :param sa_session:      SQLAlchemy database handle.

        :type  access_token: string
        :param access_token: An OIDC access token

        :return: A tuple containing the user and decoded jwt data
        :rtype: Tuple[User, dict]
        """
        raise NotImplementedError()
