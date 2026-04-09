from galaxy.authnz.oidc import GalaxyOpenIdConnect
from social_core.backends.auth0_openidconnect import Auth0OpenIdConnectAuth


class GalaxyAuth0OpenIdConnect(GalaxyOpenIdConnect, Auth0OpenIdConnectAuth):
    name = "auth0"
    EXTRA_DATA = ["id_token", "refresh_token", ("sub", "id"), "picture", "expires_in"]

