import json
import logging
import time
from typing import TYPE_CHECKING
from urllib.parse import quote

import jwt
from jwt import InvalidTokenError
from msal import ConfidentialClientApplication
from social_core.actions import (
    do_auth,
    do_complete,
    do_disconnect,
)
from social_core.backends.utils import get_backend
from social_core.strategy import BaseStrategy
from social_core.utils import (
    module_member,
    setting_name,
)
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from galaxy.exceptions import MalformedContents
from galaxy.model import (
    PSAAssociation,
    PSACode,
    PSANonce,
    PSAPartial,
    User,
    UserAuthnzToken,
)
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    ready_name_for_url,
    requests,
)
from . import IdentityProvider
from .oidc_utils import (
    decode_access_token as decode_access_token_oidc,
    is_decodable_jwt,
    is_oidc_backend,
    verify_oidc_response,
)
from ..config import GalaxyAppConfiguration

if TYPE_CHECKING:
    from social_core.backends.oauth import BaseOAuth2
    from social_core.strategy import HttpResponseProtocol

    from galaxy.managers.context import ProvidesAppContext

log = logging.getLogger(__name__)

# key: a component name which PSA requests.
# value: is the name of a class associated with that key.
DEFAULTS = {"STRATEGY": "Strategy", "STORAGE": "Storage"}

BACKENDS = {
    "google": "social_core.backends.google_openidconnect.GoogleOpenIdConnect",
    "globus": "social_core.backends.globus.GlobusOpenIdConnect",
    "elixir": "social_core.backends.elixir.ElixirOpenIdConnect",
    "lifescience": "social_core.backends.lifescience.LifeScienceOpenIdConnect",
    "einfracz": "social_core.backends.einfracz.EInfraCZOpenIdConnect",
    "nfdi": "social_core.backends.nfdi.InfraproxyOpenIdConnect",
    "okta": "social_core.backends.okta_openidconnect.OktaOpenIdConnect",
    "azure": "social_core.backends.azuread_tenant.AzureADV2TenantOAuth2",
    "egi_checkin": "social_core.backends.egi_checkin.EGICheckinOpenIdConnect",
    "oidc": "galaxy.authnz.oidc.GalaxyOpenIdConnect",
    "tapis": "galaxy.authnz.tapis.TapisOAuth2",
    "keycloak": "galaxy.authnz.keycloak.KeycloakOpenIdConnect",
    "cilogon": "galaxy.authnz.cilogon.CILogonOpenIdConnect",
}

BACKENDS_NAME = {
    "google": "google-openidconnect",
    "globus": "globus",
    "elixir": "elixir",
    "lifescience": "life_science",
    "einfracz": "e-infra_cz",
    "nfdi": "infraproxy",
    "okta": "okta-openidconnect",
    "azure": "azuread-v2-tenant-oauth2",
    "egi_checkin": "egi-checkin",
    "oidc": "oidc",
    "tapis": "tapis",
    "keycloak": "keycloak",
    "cilogon": "cilogon",
}

AUTH_PIPELINE = (
    # Get the information we can about the user and return it in a simple
    # format to create the user instance later. On some cases the details are
    # already part of the auth response from the provider, but sometimes this
    # could hit a provider API.
    "social_core.pipeline.social_auth.social_details",
    # Get the social uid from whichever service we're authing thru. The uid is
    # the unique identifier of the given user in the provider.
    "social_core.pipeline.social_auth.social_uid",
    # Verifies that the current auth process is valid within the current
    # project, this is where emails and domains allowlists are applied (if
    # defined).
    "social_core.pipeline.social_auth.auth_allowed",
    # Checks if the decoded response contains all the required fields such
    # as an ID token or a refresh token.
    "galaxy.authnz.psa_authnz.contains_required_data",
    "galaxy.authnz.psa_authnz.verify",
    # Checks if the current social-account is already associated in the site.
    "social_core.pipeline.social_auth.social_user",
    # Make up a username for this person, appends a random string at the end if
    # there's any collision.
    "social_core.pipeline.user.get_username",
    # Send a validation email to the user to verify its email address.
    # 'social_core.pipeline.mail.mail_validation',
    # Custom Galaxy step: Associates by email only if user is logged in,
    # otherwise prompts for confirmation. Replaces social_core's associate_by_email.
    "galaxy.authnz.psa_authnz.associate_by_email_if_logged_in",
    # Custom Galaxy step: Check if user creation requires confirmation.
    # If require_create_confirmation is enabled and this is a new user,
    # redirect to confirmation page instead of creating user immediately.
    "galaxy.authnz.psa_authnz.check_user_creation_confirmation",
    # Create a user account if we haven't found one yet.
    "social_core.pipeline.user.create_user",
    # Create the record that associated the social account with this user.
    "social_core.pipeline.social_auth.associate_user",
    # Populate the extra_data field in the social record with the values
    # specified by settings (and the default ones like access_token, etc).
    "social_core.pipeline.social_auth.load_extra_data",
    # Update the user record with any changed info from the auth service.
    "social_core.pipeline.user.user_details",
    "galaxy.authnz.psa_authnz.decode_access_token",
)

DISCONNECT_PIPELINE = ("galaxy.authnz.psa_authnz.allowed_to_disconnect", "galaxy.authnz.psa_authnz.disconnect")


class Redirect:
    """
    Implementation of the HttpResponseProtocol defined in social_core.strategy
    """

    def __init__(self, url: str) -> None:
        self.url = url


class PSAAuthnz(IdentityProvider):
    def __init__(self, provider, oidc_config, oidc_backend_config, app_config: GalaxyAppConfiguration):
        self.config = {"provider": provider.lower()}
        for key, value in oidc_config.items():
            self.config[setting_name(key)] = value

        self.config[setting_name("USER_MODEL")] = "models.User"
        # Use a custom auth pipeline if configured.
        auth_pipeline = app_config.oidc_auth_pipeline or AUTH_PIPELINE
        # Add extra steps to the auth pipeline if configured.
        if app_config.oidc_auth_pipeline_extra:
            auth_pipeline = auth_pipeline + tuple(app_config.oidc_auth_pipeline_extra)
        self.config["SOCIAL_AUTH_PIPELINE"] = auth_pipeline
        self.config["DISCONNECT_PIPELINE"] = DISCONNECT_PIPELINE
        self.config[setting_name("AUTHENTICATION_BACKENDS")] = (BACKENDS[provider],)

        self.config["VERIFY_SSL"] = oidc_config.get("VERIFY_SSL")
        self.config["REQUESTS_TIMEOUT"] = oidc_config.get("REQUESTS_TIMEOUT")
        self.config["ID_TOKEN_MAX_AGE"] = oidc_config.get("ID_TOKEN_MAX_AGE")
        self.config["FORCE_EMAIL_LOWERCASE"] = oidc_config.get("FORCE_EMAIL_LOWERCASE", True)
        self.config["FIXED_DELEGATED_AUTH"] = app_config.fixed_delegated_auth

        # The following config sets PSA to call the `_login_user` function for
        # logging in a user. If this setting is set to false, the `_login_user`
        # would not be called, and as a result Galaxy would not know who is
        # the just logged-in user.
        self.config[setting_name("INACTIVE_USER_LOGIN")] = True

        if provider in BACKENDS_NAME:
            self._setup_idp(oidc_backend_config)

        # Secondary AuthZ with Google identities is currently supported
        if provider != "google":
            if "SOCIAL_AUTH_SECONDARY_AUTH_PROVIDER" in self.config:
                del self.config["SOCIAL_AUTH_SECONDARY_AUTH_PROVIDER"]
            if "SOCIAL_AUTH_SECONDARY_AUTH_ENDPOINT" in self.config:
                del self.config["SOCIAL_AUTH_SECONDARY_AUTH_ENDPOINT"]

    def _is_oidc_backend(self) -> bool:
        """
        Check if the current backend is OIDC-based.

        :return: True if backend is OpenID Connect, False for OAuth2/other backends
        """
        backend_class = BACKENDS.get(self.config["provider"], "")
        return "OpenIdConnect" in backend_class or "openidconnect" in backend_class.lower()

    def _setup_idp(self, oidc_backend_config):
        """
        Configure backend-specific settings from oidc_backends_config.xml.

        Sets up both universal settings (that work for all backends) and
        OIDC-specific settings (only for OIDC backends).
        """
        # Universal settings (work for all backends: OIDC + OAuth2)
        self.config[setting_name("AUTH_EXTRA_ARGUMENTS")] = {"access_type": "offline"}
        self.config["KEY"] = oidc_backend_config.get("client_id")
        self.config["SECRET"] = oidc_backend_config.get("client_secret")
        self.config["TENANT_ID"] = oidc_backend_config.get("tenant_id")  # Azure/Tapis
        self.config["redirect_uri"] = oidc_backend_config.get("redirect_uri")
        self.config["EXTRA_SCOPES"] = oidc_backend_config.get("extra_scopes")
        self.config["LABEL"] = oidc_backend_config.get("label", self.config["provider"].capitalize())

        # Galaxy-specific pipeline settings (affect all backends)
        self.config["REQUIRE_CREATE_CONFIRMATION"] = oidc_backend_config.get("require_create_confirmation", False)

        # Optional generic settings
        if oidc_backend_config.get("prompt") is not None:
            self.config[setting_name("AUTH_EXTRA_ARGUMENTS")]["prompt"] = oidc_backend_config.get("prompt")
        if oidc_backend_config.get("api_url") is not None:
            self.config[setting_name("API_URL")] = oidc_backend_config.get("api_url")
        if oidc_backend_config.get("url") is not None:
            self.config[setting_name("URL")] = oidc_backend_config.get("url")
        if oidc_backend_config.get("username_key") is not None:
            self.config[setting_name("USERNAME_KEY")] = oidc_backend_config.get("username_key")

        # OIDC-specific settings (only set for OIDC backends)
        if self._is_oidc_backend():
            self.config["PKCE_SUPPORT"] = oidc_backend_config.get("pkce_support", False)
            self.config["IDPHINT"] = oidc_backend_config.get("idphint")
            self.config["accepted_audiences"] = oidc_backend_config.get("accepted_audiences")
            if oidc_backend_config.get("oidc_endpoint"):
                self.config["OIDC_ENDPOINT"] = oidc_backend_config["oidc_endpoint"]

    def _get_helper(self, name, do_import=False):
        this_config = self.config.get(setting_name(name), DEFAULTS.get(name, None))
        return do_import and module_member(this_config) or this_config

    def _load_backend(self, strategy, redirect_uri) -> "BaseOAuth2":
        backends = self._get_helper("AUTHENTICATION_BACKENDS")
        backend = get_backend(backends, BACKENDS_NAME[self.config["provider"]])
        return backend(strategy, redirect_uri)

    def _login_user(self, backend, user, social_user):
        self.config["user"] = user

    def refresh_azure(self, user_authnz_token):
        logging.getLogger("msal").setLevel(logging.WARN)
        old_extra_data = user_authnz_token.extra_data
        app = ConfidentialClientApplication(
            self.config["KEY"],
            self.config["SECRET"],
            authority="https://login.microsoftonline.com/" + self.config["TENANT_ID"],
        )
        extra_data = app.acquire_token_by_refresh_token(
            old_extra_data["refresh_token"], scopes=["https://graph.microsoft.com/.default"]
        )
        decoded_token = jwt.decode(extra_data["id_token"], options={"verify_signature": False})
        if "auth_time" not in extra_data:
            extra_data["auth_time"] = decoded_token["iat"]
        expires = decoded_token["exp"]
        extra_data["expires"] = int(expires - time.time())
        user_authnz_token.set_extra_data(extra_data)

    def refresh(self, trans, user_authnz_token):
        if (
            not user_authnz_token
            or not user_authnz_token.extra_data
            or "refresh_token" not in user_authnz_token.extra_data
        ):
            return False
        # refresh tokens if they reached their half lifetime
        expires = self._try_to_locate_refresh_token_expiration(user_authnz_token.extra_data)
        if not expires:
            log.debug("No `expires` or `expires_in` key found in token extra data, cannot refresh")
            return False
        if (
            int(user_authnz_token.extra_data["auth_time"]) + int(expires) / 2
            <= int(time.time())
            < int(user_authnz_token.extra_data["auth_time"]) + int(expires)
        ):
            on_the_fly_config(trans.sa_session)
            if self.config["provider"] == "azure":
                self.refresh_azure(user_authnz_token)
            else:
                strategy = Strategy(trans.request, trans.session, Storage, self.config)
                user_authnz_token.refresh_token(strategy)
            return True
        return False

    def _try_to_locate_refresh_token_expiration(self, extra_data):
        # Try to get expiration from top-level keys
        expires = extra_data.get("expires", None) or extra_data.get("expires_in", None)
        if expires:
            return expires

        # Try to get expiration from refresh_token if it's a dict
        refresh_token = extra_data.get("refresh_token")
        if refresh_token and isinstance(refresh_token, dict):
            return refresh_token.get("expires", None) or refresh_token.get("expires_in", None)

        return None

    def authenticate(self, trans, idphint=None) -> "HttpResponseProtocol":
        on_the_fly_config(trans.sa_session)
        strategy = Strategy(trans.request, trans.session, Storage, self.config)
        backend = self._load_backend(strategy, self.config["redirect_uri"])
        backend.DEFAULT_SCOPE = backend.DEFAULT_SCOPE or []
        if (
            backend.name is BACKENDS_NAME["google"]
            and "SOCIAL_AUTH_SECONDARY_AUTH_PROVIDER" in self.config
            and "SOCIAL_AUTH_SECONDARY_AUTH_ENDPOINT" in self.config
        ):
            backend.DEFAULT_SCOPE.append("https://www.googleapis.com/auth/cloud-platform")

        if self.config["EXTRA_SCOPES"] is not None:
            backend.DEFAULT_SCOPE.extend(self.config["EXTRA_SCOPES"])

        return do_auth(backend)

    def callback(self, state_token, authz_code, trans, login_redirect_url):
        on_the_fly_config(trans.sa_session)
        # Always set LOGIN_REDIRECT_URL to the base URL for pipeline steps
        # We'll adjust the final redirect based on fixed_delegated_auth after do_complete
        self.config[setting_name("LOGIN_REDIRECT_URL")] = login_redirect_url

        strategy = Strategy(trans.request, trans.session, Storage, self.config)
        strategy.session_set(f"{BACKENDS_NAME[self.config['provider']]}_state", state_token)
        backend = self._load_backend(strategy, self.config["redirect_uri"])
        redirect = do_complete(
            backend,
            login=lambda backend, user, social_user: self._login_user(backend, user, social_user),
            user=trans.user,
            state=state_token,
        )
        redirect_url = redirect.url if hasattr(redirect, "url") else redirect

        user = self.config.get("user", None)

        # Determine if this was a new association
        # The associate_by_email_if_logged_in pipeline step sets this flag based on whether
        # the social_user (UserAuthnzToken) already existed before associate_user
        is_new_association = self.config.get("IS_NEW_ASSOCIATION", True)

        # Adjust redirect URL based on fixed_delegated_auth setting
        # Check if this is a successful authentication (not a redirect to login/start or confirmation)
        fixed_delegated_auth = self.config.get("FIXED_DELEGATED_AUTH", False)
        email_exists = self.config.get("EMAIL_EXISTS")  # Set by pipeline if email matches different user

        if redirect_url and isinstance(redirect_url, str) and not redirect_url.startswith("?"):
            # Check if PSA returned a redirect to login/start or confirmation page
            # If so, keep it as-is (don't modify for these special cases)
            if "login/start" not in redirect_url and "?confirm" not in redirect_url:
                # This is a successful authentication redirect
                if is_new_association:
                    # New association - redirect based on fixed_delegated_auth
                    if not fixed_delegated_auth:
                        # Redirect to user/external_ids
                        redirect_url = f"{login_redirect_url}user/external_ids"
                    else:
                        # Redirect to root for fixed_delegated_auth
                        redirect_url = login_redirect_url
                else:
                    # Repeat login - redirect to root
                    redirect_url = login_redirect_url

            # Add notification and email_exists parameters only for new associations
            if "?confirm" not in redirect_url and "login/start" not in redirect_url and is_new_association:
                provider_label = self.config.get("LABEL", self.config["provider"].capitalize())
                separator = "&" if "?" in redirect_url else "?"
                notification_msg = quote(f"Your {provider_label} identity has been linked to your Galaxy account.")
                redirect_url = f"{redirect_url}{separator}notification={notification_msg}"

                # Add email_exists parameter if identity email matched a different account
                if email_exists:
                    redirect_url = f"{redirect_url}&email_exists={quote(email_exists)}"

        return redirect_url, user

    def disconnect(self, provider, trans, disconnect_redirect_url=None, email=None, association_id=None):
        on_the_fly_config(trans.sa_session)
        self.config[setting_name("DISCONNECT_REDIRECT_URL")] = (
            disconnect_redirect_url if disconnect_redirect_url is not None else ()
        )
        strategy = Strategy(trans.request, trans.session, Storage, self.config)
        backend = self._load_backend(strategy, self.config["redirect_uri"])
        response = do_disconnect(backend, trans.user, association_id)
        response_url = response.url if hasattr(response, "url") else response
        if isinstance(response_url, str):
            return True, "", response_url
        return response.get("success", False), response.get("message", ""), ""

    def logout(self, trans, post_user_logout_href=None):
        """
        Logout from the identity provider.

        For OIDC backends, constructs a logout URL using the end_session_endpoint.
        For non-OIDC backends, returns the fallback URL.

        :param trans: Galaxy transaction object
        :param post_user_logout_href: URL to redirect to after logout
        :return: Logout redirect URI
        """
        on_the_fly_config(trans.sa_session)
        strategy = Strategy(trans.request, trans.session, Storage, self.config)
        backend = self._load_backend(strategy, self.config["redirect_uri"])

        # Only OIDC backends support IDP logout
        if is_oidc_backend(backend):
            try:
                # Get end_session_endpoint from OIDC discovery document
                oidc_config = backend.oidc_config()
                end_session_endpoint = oidc_config.get("end_session_endpoint")

                if end_session_endpoint:
                    # Construct logout URL with optional redirect_uri
                    if post_user_logout_href:
                        logout_url = f"{end_session_endpoint}?redirect_uri={quote(post_user_logout_href)}"
                    else:
                        logout_url = end_session_endpoint

                    return logout_url
                else:
                    # No end_session_endpoint available
                    log.warning(f"No end_session_endpoint found for {self.config['provider']}")
                    return post_user_logout_href or "/"

            except Exception as e:
                log.exception(f"Error getting logout URL for {self.config['provider']}: {e}")
                return post_user_logout_href or "/"
        else:
            # Non-OIDC backends don't have IDP logout
            log.debug(f"Backend {self.config['provider']} does not support IDP logout")
            return post_user_logout_href or "/"

    def decode_user_access_token(self, sa_session, access_token):
        """
        Verifies and decodes an access token against this provider, returning the user and
        a dict containing the decoded token data.

        This is used for API authentication with Bearer tokens. Only works for OIDC backends.

        :param sa_session: SQLAlchemy database session
        :param access_token: An OIDC access token
        :return: A tuple containing the user and decoded jwt data, or (None, None) if token is for different provider
        :rtype: Tuple[User, dict]
        :raises Exception: If token is valid but user hasn't logged in, or token validation fails
        :raises NotImplementedError: If backend is not OIDC-based
        """
        # Only OIDC backends support JWT access tokens
        if not self._is_oidc_backend():
            raise NotImplementedError(f"Access token decoding not supported for {self.config['provider']}")

        try:
            on_the_fly_config(sa_session)
            # Create a minimal strategy and backend just for token verification
            strategy = Strategy(None, {}, Storage, self.config)
            backend = self._load_backend(strategy, self.config["redirect_uri"])

            # Decode and verify the access token using oidc_utils
            # This will raise exceptions for: expired tokens, invalid audience, invalid signature, etc.
            assert is_oidc_backend(backend)
            decoded_jwt = decode_access_token_oidc(access_token, backend)

            # JWT verified, now fetch the user
            user_id = decoded_jwt["sub"]

            # Look up the user by their OIDC uid
            user_authnz_token = (
                sa_session.query(UserAuthnzToken)
                .filter(
                    UserAuthnzToken.uid == user_id, UserAuthnzToken.provider == BACKENDS_NAME[self.config["provider"]]
                )
                .first()
            )

            user = user_authnz_token.user if user_authnz_token else None

            if not user:
                # User hasn't logged in via OIDC at least once
                # Return (None, decoded_jwt) to signal that token is valid but user is not registered
                return None, decoded_jwt

            return user, decoded_jwt

        except jwt.exceptions.InvalidIssuerError:
            # Token is for a different provider - return (None, None) to try next provider
            log.debug(f"Invalid issuer for access token with provider: {self.config['provider']}")
            return None, None
        except Exception:
            # Any other exception (expired token, invalid audience, etc.) should be raised
            # so the authentication fails with a proper error message
            raise

    def create_user(self, token: str, trans: "ProvidesAppContext", login_redirect_url: str):
        """
        Create a user from a stored token (deferred user creation).

        This is used when require_create_confirmation is enabled. After the user
        confirms they want to create an account, this method completes the user
        creation process using the stored token from the authentication callback.

        :param token: JSON-encoded token from the initial authentication
        :param trans: Galaxy transaction object
        :param login_redirect_url: URL to redirect after user creation
        :return: Tuple of (redirect_url, user)
        """
        on_the_fly_config(trans.sa_session)
        token_dict = json.loads(token)

        # Decode the ID token to get user info
        id_token = token_dict.get("id_token")
        if not id_token:
            raise Exception("Missing id_token in stored authentication data")

        # Decode without verification (already verified during initial auth)
        userinfo = jwt.decode(id_token, options={"verify_signature": False})

        email = userinfo.get("email")
        assert email is not None
        username = userinfo.get("preferred_username", email)
        if "@" in username:
            username = username.split("@")[0]

        # Clean username for Galaxy
        username = ready_name_for_url(username).lower()

        # Check if username already exists, append number if needed
        if trans.sa_session.query(User).filter_by(username=username).first():
            count = 0
            while trans.sa_session.query(User).filter_by(username=f"{username}{count}").first():
                count += 1
            username = f"{username}{count}"

        # Create the user
        user = trans.app.user_manager.create(email=email, username=username)
        if trans.app.config.user_activation_on:
            trans.app.user_manager.send_activation_email(trans, email, username)

        # Create the UserAuthnzToken record
        user_id = userinfo.get("sub")
        user_authnz_token = UserAuthnzToken(
            user=user, uid=user_id, provider=BACKENDS_NAME[self.config["provider"]], extra_data=token_dict
        )

        trans.sa_session.add(user)
        trans.sa_session.add(user_authnz_token)
        trans.sa_session.commit()

        return login_redirect_url, user


class Strategy(BaseStrategy):
    def __init__(self, request, session, storage, config, tpl=None):
        self.request = request
        self.session = session if session else {}
        self.config = config
        self.config["SOCIAL_AUTH_REDIRECT_IS_HTTPS"] = (
            True if self.request and self.request.host.startswith("https:") else False
        )
        self.config["SOCIAL_AUTH_GOOGLE_OPENIDCONNECT_EXTRA_DATA"] = ["id_token"]
        super().__init__(storage, tpl)

    def get_setting(self, name):
        return self.config[name]

    def session_get(self, name, default=None):
        return self.session.get(name, default)

    def session_set(self, name, value):
        self.session[name] = value

    def session_pop(self, name):
        raise NotImplementedError("Not implemented.")

    def request_data(self, merge=True):
        if not self.request:
            return {}
        if merge:
            data = self.request.GET.copy()
            data.update(self.request.POST)
        elif self.request.method == "POST":
            data = self.request.POST
        else:
            data = self.request.GET
        return data

    def request_host(self):
        if self.request:
            return self.request.host

    def build_absolute_uri(self, path=None):
        path = path or ""
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if self.request:
            return (
                self.request.host + "/authnz" + ("/" + self.config.get("provider"))
                if self.config.get("provider", None) is not None
                else ""
            )
        return path

    def redirect(self, url: str) -> Redirect:
        return Redirect(url)

    def html(self, content):
        raise NotImplementedError("Not implemented.")

    def render_html(self, tpl=None, html=None, context=None):
        raise NotImplementedError("Not implemented.")


class Storage:
    user = UserAuthnzToken
    nonce = PSANonce
    association = PSAAssociation
    code = PSACode
    partial = PSAPartial

    @classmethod
    def is_integrity_error(cls, exception):
        return exception.__class__ is IntegrityError


def on_the_fly_config(sa_session):
    PSACode.sa_session = sa_session
    UserAuthnzToken.sa_session = sa_session
    PSANonce.sa_session = sa_session
    PSAPartial.sa_session = sa_session
    PSAAssociation.sa_session = sa_session


def contains_required_data(response=None, is_new=False, backend=None, **kwargs):
    """
    This function is called as part of authentication and authorization
    pipeline before user is authenticated or authorized (see AUTH_PIPELINE).

    This function asserts if all the data required by Galaxy for a user
    is provided. It raises an exception if any of the required data is missing,
    and returns void if otherwise.

    For OIDC backends, verifies presence of id_token and iat claim.
    For OAuth2 backends, performs basic validation only.

    :type  response: dict
    :param response:  a dictionary containing decoded response from
                      OIDC backend that contain the following keys
                      among others:

                        -   id_token;       see: http://openid.net/specs/openid-connect-core-1_0.html#IDToken
                        -   access_token;   see: https://tools.ietf.org/html/rfc6749#section-1.4
                        -   refresh_token;  see: https://tools.ietf.org/html/rfc6749#section-1.5
                        -   token_type;     see: https://tools.ietf.org/html/rfc6750#section-6.1.1
                        -   scope;          see: http://openid.net/specs/openid-connect-core-1_0.html#AuthRequest
                        -   expires_in;     is the expiration time of the access and ID tokens in seconds since
                                            the response was generated.

    :type  is_new: bool
    :param is_new: has the user been authenticated?

    :param backend: The PSA backend being used for authentication

    :param kwargs:      may contain the following keys among others:

                        -   uid:        user ID
                        -   user:       Galaxy user; if user is already authenticated
                        -   storage:    an instance of Storage class.
                        -   strategy:   an instance of the Strategy class.
                        -   state:      the state code received from identity provider.
                        -   details:    details about the user's third-party identity as requested in `scope`.

    :rtype:  void
    :return: Raises an exception if any of the required arguments is missing, and pass if all are given.
    """
    hint_msg = (
        "Visit the identity provider's permitted applications page "
        "(e.g., visit `https://myaccount.google.com/u/0/permissions` "
        "for Google), then revoke the access of this Galaxy instance, "
        "and then retry to login. If the problem persists, contact "
        "the Admin of this Galaxy instance."
    )
    if response is None or not isinstance(response, dict):
        # This can happen only if PSA is not able to decode the `authnz code`
        # sent back from the identity provider. PSA internally handles such
        # scenarios; however, this case is implemented to prevent uncaught
        # server-side errors.
        raise MalformedContents(err_msg=f"`response` not found. {hint_msg}")

    # OIDC-specific validation
    if backend and is_oidc_backend(backend):
        try:
            verify_oidc_response(response)
        except MalformedContents:
            # Re-raise with hint message
            raise MalformedContents(err_msg=f"Missing required OIDC data. {hint_msg}")

    if is_new and not response.get("refresh_token"):
        # An identity provider (e.g., Google) sends a refresh token the first
        # time user consents Galaxy's access (i.e., the first time user logs in
        # to a galaxy instance using their credentials with the identity provider).
        # There could be variety of scenarios under which a refresh token might
        # be missing; e.g., a manipulated Galaxy's database, where a user's records
        # from galaxy_user and oidc_user_authnz_tokens tables deleted after the
        # user has provided consent. This can also happen under dev efforts.
        # The solution is to revoke the consent by visiting the identity provider's
        # website, and then retry the login process.
        raise MalformedContents(err_msg=f"Missing refresh token. {hint_msg}")


def verify(strategy=None, response=None, details=None, **kwargs):
    provider = strategy.config.get("SOCIAL_AUTH_SECONDARY_AUTH_PROVIDER")
    endpoint = strategy.config.get("SOCIAL_AUTH_SECONDARY_AUTH_ENDPOINT")
    if provider is None or endpoint is None:
        # Either the secondary authorization is not configured or OIDC IdP
        # is not compatible, so allow user login.
        return

    if provider.lower() == "gcp":
        result = requests.post(
            f"https://iam.googleapis.com/v1/projects/-/serviceAccounts/{endpoint}:getIamPolicy",
            headers={
                "Authorization": f"Bearer {response.get('access_token')}",
                "Accept": "application/json",
            },
            timeout=DEFAULT_SOCKET_TIMEOUT,
        )
        res = json.loads(result.content)
        if result.status_code == requests.codes.ok:
            email_addresses = res["bindings"][0]["members"]
            email_addresses = [x.lower().replace("user:", "").strip() for x in email_addresses]
            if details.get("email") in email_addresses:
                # Secondary authorization successful, so allow user login.
                pass
            else:
                raise Exception("Not authorized by GCP IAM.")
        else:
            # The message of the raised exception is shown to the user; hence,
            # the following way of handling exception is better than using
            # result.raise_for_status(), since raise_for_status may report
            # sensitive information that should not be exposed to users.
            raise Exception(res["error"]["message"])
    else:
        raise Exception(f"`{provider}` is an unsupported secondary authorization provider, contact admin.")


def allowed_to_disconnect(
    name=None, user=None, user_storage=None, strategy=None, backend=None, request=None, details=None, **kwargs
):
    """
    Disconnect is the process of disassociating a Galaxy user and a third-party authnz.
    In other words, it is the process of removing any access and/or ID tokens of a user.
    This function should raise an exception if disconnection is NOT permitted. Do NOT
    return any value (except an empty dictionary) if disconnect is allowed. Because, at
    least until PSA social_core v.1.5.0, any returned value (e.g., Boolean) will result
    in ignoring the rest of the disconnect pipeline.
    See the following condition in `run_pipeline` function:
    https://github.com/python-social-auth/social-core/blob/master/social_core/backends/base.py#L114
    :param name: name of the backend (e.g., google-openidconnect)
    :type user: galaxy.model.User
    :type user_storage: galaxy.model.UserAuthnzToken
    :type strategy: galaxy.authnz.psa_authnz.Strategy
    :type backend: PSA backend object (e.g., social_core.backends.google_openidconnect.GoogleOpenIdConnect)
    :type request: webob.multidict.MultiDict
    :type details: dict
    :return: empty dict
    """
    pass


def disconnect(
    name=None, user=None, user_storage=None, strategy=None, backend=None, request=None, details=None, **kwargs
):
    """
    Disconnect is the process of disassociating a Galaxy user and a third-party authnz.
    In other words, it is the process of removing any access and/or ID tokens of a user.
    :param name: name of the backend (e.g., google-openidconnect)
    :type user: galaxy.model.User
    :type user_storage: galaxy.model.UserAuthnzToken
    :type strategy: galaxy.authnz.psa_authnz.Strategy
    :type backend: PSA backend object (e.g., social_core.backends.google_openidconnect.GoogleOpenIdConnect)
    :type request: webob.multidict.MultiDict
    :type details: dict
    :return: void or empty dict. Any key-value pair inside the dictionary will be available
    inside PSA only, and will be passed to the next step in the disconnect pipeline. However,
    the key-value pair will not be returned as a result of calling the `do_disconnect` function.
    Additionally, returning any value except for a(n) (empty) dictionary, will break the
    disconnect pipeline, and that value will be returned as a result of calling the `do_disconnect` function.
    """

    sa_session = user_storage.sa_session
    user_authnz = (
        sa_session.query(user_storage)
        .filter(user_storage.table.c.user_id == user.id, user_storage.table.c.provider == name)
        .first()
    )
    if user_authnz is None:
        return {"success": False, "message": "Not authenticated by any identity providers."}
    # option A
    sa_session.delete(user_authnz)
    # option B
    # user_authnz.extra_data = None
    sa_session.commit()


def decode_access_token(social: UserAuthnzToken, backend, **kwargs):
    """
    Auth pipeline step to decode the OIDC access token, if possible.

    Note that some OIDC providers return an opaque access token, which
    cannot be decoded. This step only works for OIDC backends.

    Returns the access token, making it available as a new argument
    "access_token" that can be used in future pipeline steps. If
    decoding the access token is not possible, access_token will be None.

    Depends on "access_token" being present in social.extra_data,
    which should be handled by social_core.pipeline.social_auth.load_extra_data, so
    this step should be placed after load_extra_data in the pipeline.
    """
    # Only decode for OIDC backends
    if not is_oidc_backend(backend):
        return {"access_token": None}

    if social.extra_data is None:
        return {"access_token": None}
    access_token_encoded = social.extra_data.get("access_token")
    if access_token_encoded is None:
        return {"access_token": None}
    if not is_decodable_jwt(access_token_encoded):
        log.warning(
            "Access token is not in header.payload.signature format and can't be decoded (may be an opaque token)"
        )
        return {"access_token": None}
    try:
        access_token_data = decode_access_token_oidc(token_str=access_token_encoded, backend=backend)
    except InvalidTokenError as e:
        log.warning(f"Access token couldn't be decoded: {e}")
        return {"access_token": None}
    return {"access_token": access_token_data}


def associate_by_email_if_logged_in(
    strategy=None, backend=None, details=None, user=None, social=None, is_new=False, *args, **kwargs
):
    """
    Custom pipeline step to handle email-based account association.

    This replaces social_core.pipeline.social_auth.associate_by_email with Galaxy-specific logic:
    - If user is currently logged in (passed from trans.user): auto-associate the OIDC identity
      - If identity email matches a different user's account, store that info for notification
    - If user is NOT logged in but an account with that email exists:
      - If fixed_delegated_auth is enabled: auto-associate with existing user
      - Otherwise: prompt for confirmation
    - If no account exists: continue with user creation

    Returns a dict with 'user' if association happened, or a redirect URL to stop the pipeline.
    """
    # Track if this is a new association by checking if social (UserAuthnzToken) already exists
    # The social_user step (which runs before this) sets social=UserAuthnzToken if exists, or None
    if social is not None:
        # Association already exists - this is a repeat login
        strategy.config["IS_NEW_ASSOCIATION"] = False
    else:
        # No association exists yet - this will be a new association
        strategy.config["IS_NEW_ASSOCIATION"] = True

    email = details.get("email")
    if not email:
        # No email to match, continue with user creation
        return

    # Check if an account with this email exists
    # sa_session is guaranteed to be set by on_the_fly_config() before pipeline runs
    sa_session = UserAuthnzToken.sa_session
    if sa_session is None:
        raise RuntimeError("sa_session must be set by on_the_fly_config before pipeline execution")
    existing_user = sa_session.query(User).where(func.lower(User.email) == email.lower()).first()

    if user:
        # User is already logged in (from trans.user in callback) or was found by social_user step
        # Check if the identity email matches a different user's account
        if existing_user and existing_user.id != user.id:
            # Store this info so callback can add email_exists parameter
            strategy.config["EMAIL_EXISTS"] = email
        # Proceed with association to the logged-in user
        return

    # User is not logged in - check if an account with this email exists
    if existing_user:
        # Check if fixed_delegated_auth is enabled
        fixed_delegated_auth = strategy.config.get("FIXED_DELEGATED_AUTH", False)

        if fixed_delegated_auth:
            # Auto-associate the OIDC identity with the existing user
            # Return the user to continue the pipeline with association
            return {"user": existing_user}

        # An account exists but user is not logged in and fixed_delegated_auth is False
        # Redirect to page prompting user to log in and link accounts
        provider = strategy.config.get("provider", "unknown")
        login_redirect_url = strategy.config.get(setting_name("LOGIN_REDIRECT_URL"), "/")

        redirect_url = (
            f"{login_redirect_url}login/start"
            f"?connect_external_provider={provider}"
            f"&connect_external_email={quote(email)}"
            f"&connect_external_label={strategy.config.get('LABEL', provider.capitalize())}"
        )

        # Return the redirect URL - PSA will use this to redirect and stop the pipeline
        strategy.session_set("redirect_url", redirect_url)
        return redirect_url

    # No existing user, continue with user creation
    return


def check_user_creation_confirmation(
    strategy=None, backend=None, details=None, response=None, is_new=False, user=None, **kwargs
):
    """
    Pipeline step to handle deferred user creation (require_create_confirmation).

    This was a feature from custos where new users could be shown a confirmation
    page before their account is created. If require_create_confirmation is enabled
    and this is a new user (no existing Galaxy account), the pipeline is interrupted
    and the user is redirected to a confirmation page with the token stored for later.

    This step should be placed before create_user in the pipeline.
    """
    require_confirmation = strategy.config.get("REQUIRE_CREATE_CONFIRMATION", False)

    # Only apply if confirmation is required, this is a new association, and no user exists yet
    if require_confirmation and is_new and not user:
        # Check if there's an existing user with this email
        email = details.get("email")
        if email:
            # sa_session is guaranteed to be set by on_the_fly_config() before pipeline runs
            sa_session = UserAuthnzToken.sa_session
            if sa_session is None:
                raise RuntimeError("sa_session must be set by on_the_fly_config before pipeline execution")
            existing_user = sa_session.query(User).where(func.lower(User.email) == email.lower()).first()

            # If no existing user, redirect to confirmation page
            if not existing_user:
                provider = strategy.config.get("provider", "unknown")
                login_redirect_url = strategy.config.get(setting_name("LOGIN_REDIRECT_URL"), "/")

                # Store the token response for later use
                token_json = json.dumps(response)

                # Store in session for the create_user_from_token endpoint
                strategy.session_set(f"pending_oidc_token_{provider}", token_json)

                # Construct redirect URL to confirmation page
                redirect_url = (
                    f"{login_redirect_url}login/start"
                    f"?confirm=true"
                    f"&provider_token={quote(token_json)}"
                    f"&provider={provider}"
                )

                # Return the redirect URL - PSA will detect this and stop the pipeline
                # This prevents user creation until they confirm
                return redirect_url

    # Continue with user creation if confirmation is not required or user already exists
    return
