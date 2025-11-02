"""
Enhanced CILogon OpenID Connect backend for Galaxy.

This backend extends PSA's OpenIdConnectAuth with CILogon-specific features
"""
import logging
import os

from pkce import generate_pkce_pair
from social_core.backends.open_id_connect import OpenIdConnectAuth

log = logging.getLogger(__name__)


class CILogonOpenIdConnect(OpenIdConnectAuth):
    name = "cilogon"

    # CILogon-specific scopes
    DEFAULT_SCOPE = ["openid", "email", "profile", "org.cilogon.userinfo"]

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

    def auth_params(self, state=None):
        """
        Add CILogon-specific parameters to the authorization request.
        """
        params = super().auth_params(state)

        # Add CILogon idp hint if configured
        idphint = self.setting("IDPHINT", "cilogon")
        if idphint:
            params["idphint"] = idphint

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
