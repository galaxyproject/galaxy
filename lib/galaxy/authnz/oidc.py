"""
Base OpenID Connect backend for Galaxy.

This module provides GalaxyOpenIdConnect, a base class for all Galaxy OIDC backends
that extends PSA's OpenIdConnectAuth with Galaxy-specific features:
- PKCE support
- Localhost development mode
- Refresh token support
- Customizable IDP hints

Specific providers (Keycloak, CILogon, etc.) should inherit from this class.
"""
import logging
import os

from pkce import generate_pkce_pair
from social_core.backends.open_id_connect import OpenIdConnectAuth

log = logging.getLogger(__name__)


class GalaxyOpenIdConnect(OpenIdConnectAuth):
    """
    Base OIDC backend for Galaxy with common enhancements.

    This class provides functionality common to all Galaxy OIDC providers:
    - PKCE (Proof Key for Code Exchange) support for enhanced security
    - Localhost development mode with relaxed SSL requirements
    - Refresh token support
    """

    # Backend name - must be overridden in subclasses
    name = "oidc"

    # PKCE support - can be enabled via configuration
    PKCE_ENABLED = False

    # Support refresh tokens via POST method
    REFRESH_TOKEN_METHOD = "POST"

    def __init__(self, *args, **kwargs):
        """Initialize the backend and check for PKCE configuration."""
        super().__init__(*args, **kwargs)
        # Check if PKCE is enabled via strategy config
        self.PKCE_ENABLED = self.setting("PKCE_SUPPORT", False)

    def auth_params(self, state=None):
        """
        Add Galaxy-specific parameters to the authorization request.

        This method adds:
        - PKCE parameters (if enabled)
        """
        params = super().auth_params(state)

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

        Override to enable localhost development mode with relaxed SSL requirements.
        For security, this ONLY applies to http://localhost: URLs.
        """
        # Allow insecure transport ONLY for HTTP (not HTTPS) localhost development
        if self.redirect_uri and self.redirect_uri.startswith("http://localhost:"):
            if os.environ.get("OAUTHLIB_INSECURE_TRANSPORT") != "1":
                log.warning("Setting OAUTHLIB_INSECURE_TRANSPORT to '1' for localhost development")
                os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        return super().user_data(access_token, *args, **kwargs)
