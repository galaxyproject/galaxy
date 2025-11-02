"""
Enhanced Keycloak OpenID Connect backend for Galaxy.

This backend extends PSA's OpenIdConnectAuth with Keycloak-specific features
"""
import logging
import os

from pkce import generate_pkce_pair
from social_core.backends.open_id_connect import OpenIdConnectAuth

log = logging.getLogger(__name__)


class KeycloakOpenIdConnect(OpenIdConnectAuth):
    name = "keycloak"

    # Use PKCE if enabled in configuration
    PKCE_ENABLED = False

    # Support refresh tokens
    REFRESH_TOKEN_METHOD = "POST"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if PKCE is enabled via strategy config
        self.PKCE_ENABLED = self.setting("PKCE_SUPPORT", False)

    def oidc_endpoint(self):
        """
        Return the OIDC endpoint for configuration discovery.

        Keycloak typically uses URLs like:
        https://keycloak.example.com/realms/myrealm
        """
        # Check if custom URL is configured
        base_url = self.setting("URL")
        if base_url:
            # Remove potential trailing slash
            return base_url.rstrip("/")
        # Fall back to default OIDC endpoint discovery
        return super().oidc_endpoint()

    def auth_params(self, state=None):
        """
        Add Keycloak-specific parameters to the authorization request.s
        """
        params = super().auth_params(state)

        # Add Keycloak idp hint if configured
        idphint = self.setting("IDPHINT", "oidc")
        if idphint:
            params["kc_idp_hint"] = idphint

        # Add PKCE parameters if enabled
        if self.PKCE_ENABLED:
            # Generate PKCE challenge
            code_verifier, code_challenge = generate_pkce_pair(code_length=96)
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"
            # Store verifier in session for later use
            self.strategy.session_set("pkce_code_verifier", code_verifier)

        return params

    def auth_complete_params(self, state=None):
        """
        Add PKCE code verifier to token request if PKCE is enabled.
        """
        params = super().auth_complete_params(state)

        # Add PKCE code verifier if it was used
        if self.PKCE_ENABLED:
            code_verifier = self.strategy.session_get("pkce_code_verifier")
            if code_verifier:
                params["code_verifier"] = code_verifier
                # Clean up the session
                try:
                    self.strategy.session_pop("pkce_code_verifier")
                except NotImplementedError:
                    # Strategy.session_pop is not implemented, that's ok
                    pass

        return params

    def get_jwks_keys(self):
        """
        Get JWKS keys from the OIDC provider for token verification.

        This enables proper JWT signature verification using the provider's
        public keys.

        Returns the 'keys' array from the JWKS document.
        """
        oidc_config = self.oidc_config()
        jwks_uri = oidc_config.get("jwks_uri")
        if jwks_uri:
            jwks_response = self.get_json(jwks_uri)
            # The JWKS document has a 'keys' array containing the actual keys
            return jwks_response.get("keys", [])
        return []

    def user_data(self, access_token, *args, **kwargs):
        """
        Fetch user data from the userinfo endpoint.

        Override to ensure SSL verification settings are respected.
        """
        # Allow insecure transport ONLY for HTTP (not HTTPS) localhost development
        if self.redirect_uri and self.redirect_uri.startswith("http://localhost:"):
            if os.environ.get("OAUTHLIB_INSECURE_TRANSPORT") != "1":
                log.warning("Setting OAUTHLIB_INSECURE_TRANSPORT to '1' for localhost development")
                os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        return super().user_data(access_token, *args, **kwargs)
