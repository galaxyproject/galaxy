"""
CILogon OpenID Connect backend for Galaxy.

This backend extends Galaxy's base OIDC implementation with CILogon-specific features.
"""

from galaxy.authnz.oidc import GalaxyOpenIdConnect


class CILogonOpenIdConnect(GalaxyOpenIdConnect):
    """
    CILogon OIDC backend for Galaxy.

    Inherits PKCE support, localhost development mode, and refresh token support
    from GalaxyOpenIdConnect. Adds CILogon-specific configuration:
    - CILogon-specific scopes including org.cilogon.userinfo
    - Custom URL handling to strip /authorize suffix
    - CILogon-specific IDP hint parameter (idphint)
    """

    name = "cilogon"

    # CILogon-specific scopes
    DEFAULT_SCOPE = ["openid", "email", "profile", "org.cilogon.userinfo"]

    def auth_params(self, state=None):
        """
        Add CILogon-specific parameters to the authorization request.

        Adds idphint parameter for CILogon IDP selection.
        """
        params = super().auth_params(state)

        # Add CILogon IDP hint (default: "cilogon")
        idphint = self.setting("IDPHINT", "cilogon")
        if idphint:
            params["idphint"] = idphint

        return params

    def oidc_endpoint(self):
        """
        Return the OIDC endpoint for configuration discovery.

        CILogon URLs may include /authorize in examples, which needs to be
        stripped to find the correct base URL.

        Example CILogon URL:
        https://cilogon.org/authorize -> https://cilogon.org
        """
        # Check if custom URL is configured
        base_url = self.setting("URL")
        if base_url:
            # Backwards compatibility: CILogon URL is sometimes given with /authorize
            # Remove it to get the correct openid configuration endpoint
            if base_url.endswith("/authorize"):
                base_url = "/".join(base_url.split("/")[:-1])
            # Remove potential trailing slash
            return base_url.rstrip("/")
        # Fall back to default OIDC endpoint discovery
        return super().oidc_endpoint()
