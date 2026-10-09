"""
Keycloak OpenID Connect backend for Galaxy.

This backend extends Galaxy's base OIDC implementation with Keycloak-specific features.
"""

from galaxy.authnz.oidc import GalaxyOpenIdConnect


class KeycloakOpenIdConnect(GalaxyOpenIdConnect):
    """
    Keycloak OIDC backend for Galaxy.

    Inherits PKCE support, localhost development mode, and refresh token support
    from GalaxyOpenIdConnect. Adds Keycloak-specific configuration:
    - Custom URL endpoint handling
    - Keycloak-specific IDP hint parameter (kc_idp_hint)
    """

    name = "keycloak"

    def auth_params(self, state=None):
        """
        Add Keycloak-specific parameters to the authorization request.

        Adds kc_idp_hint parameter for Keycloak IDP routing.
        """
        params = super().auth_params(state)

        # Add Keycloak IDP hint (default: "oidc")
        if idphint := self.setting("IDPHINT", "oidc"):
            params["kc_idp_hint"] = idphint

        return params

    def oidc_endpoint(self):
        """
        Return the OIDC endpoint for configuration discovery.

        Keycloak typically uses URLs like:
        https://keycloak.example.com/realms/myrealm

        This allows administrators to configure the full Keycloak realm URL.
        """
        # Check if custom URL is configured
        if base_url := self.setting("URL"):
            # Remove potential trailing slash
            return base_url.rstrip("/")
        # Fall back to default OIDC endpoint discovery
        return super().oidc_endpoint()
