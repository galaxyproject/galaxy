import json
import logging
import time

from urllib.parse import quote

import jwt
from jwt import InvalidTokenError
from msal import ConfidentialClientApplication
from social_core.actions import (
    do_auth,
    do_complete,
    do_disconnect,
)
from social_core.backends.open_id_connect import OpenIdConnectAuth
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
from ..config import GalaxyAppConfiguration

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
    # Set appropriate redirect URL based on context
    "galaxy.authnz.psa_authnz.set_redirect_url",
)

DISCONNECT_PIPELINE = ("galaxy.authnz.psa_authnz.allowed_to_disconnect", "galaxy.authnz.psa_authnz.disconnect")


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

    def _setup_idp(self, oidc_backend_config):
        self.config[setting_name("AUTH_EXTRA_ARGUMENTS")] = {"access_type": "offline"}
        self.config["KEY"] = oidc_backend_config.get("client_id")
        self.config["SECRET"] = oidc_backend_config.get("client_secret")
        self.config["TENANT_ID"] = oidc_backend_config.get("tenant_id")
        self.config["redirect_uri"] = oidc_backend_config.get("redirect_uri")
        self.config["accepted_audiences"] = oidc_backend_config.get("accepted_audiences")
        self.config["EXTRA_SCOPES"] = oidc_backend_config.get("extra_scopes")

        # OIDC-specific configurations
        self.config["PKCE_SUPPORT"] = oidc_backend_config.get("pkce_support", False)
        self.config["IDPHINT"] = oidc_backend_config.get("idphint")
        self.config["REQUIRE_CREATE_CONFIRMATION"] = oidc_backend_config.get("require_create_confirmation", False)
        self.config["LABEL"] = oidc_backend_config.get("label", self.config["provider"].capitalize())

        if oidc_backend_config.get("oidc_endpoint"):
            self.config["OIDC_ENDPOINT"] = oidc_backend_config["oidc_endpoint"]
        if oidc_backend_config.get("prompt") is not None:
            self.config[setting_name("AUTH_EXTRA_ARGUMENTS")]["prompt"] = oidc_backend_config.get("prompt")
        if oidc_backend_config.get("api_url") is not None:
            self.config[setting_name("API_URL")] = oidc_backend_config.get("api_url")
        if oidc_backend_config.get("url") is not None:
            self.config[setting_name("URL")] = oidc_backend_config.get("url")
        if oidc_backend_config.get("username_key") is not None:
            self.config[setting_name("USERNAME_KEY")] = oidc_backend_config.get("username_key")

    def _get_helper(self, name, do_import=False):
        this_config = self.config.get(setting_name(name), DEFAULTS.get(name, None))
        return do_import and module_member(this_config) or this_config

    def _load_backend(self, strategy, redirect_uri):
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

    def authenticate(self, trans, idphint=None):
        on_the_fly_config(trans.sa_session)
        strategy = Strategy(trans.request, trans.session, Storage, self.config)
        backend = self._load_backend(strategy, self.config["redirect_uri"])
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
        self.config[setting_name("LOGIN_REDIRECT_URL")] = login_redirect_url
        strategy = Strategy(trans.request, trans.session, Storage, self.config)
        strategy.session_set(f"{BACKENDS_NAME[self.config['provider']]}_state", state_token)
        backend = self._load_backend(strategy, self.config["redirect_uri"])
        redirect_url = do_complete(
            backend,
            login=lambda backend, user, social_user: self._login_user(backend, user, social_user),
            user=trans.user,
            state=state_token,
        )

        user = self.config.get("user", None)

        # Add notification message to redirect URL if authentication succeeded
        # Check if we successfully authenticated/linked an account
        if redirect_url and isinstance(redirect_url, str) and not redirect_url.startswith("?"):
            # Get provider label for the notification message
            provider_label = self.config.get("LABEL", self.config["provider"].capitalize())

            # Check if the redirect already has query parameters
            separator = "&" if "?" in redirect_url else "?"

            # Add notification message
            notification_msg = quote(f"Your {provider_label} identity has been linked to your Galaxy account.")
            redirect_url = f"{redirect_url}{separator}notification={notification_msg}"

        return redirect_url, user

    def disconnect(self, provider, trans, disconnect_redirect_url=None, email=None, association_id=None):
        on_the_fly_config(trans.sa_session)
        self.config[setting_name("DISCONNECT_REDIRECT_URL")] = (
            disconnect_redirect_url if disconnect_redirect_url is not None else ()
        )
        strategy = Strategy(trans.request, trans.session, Storage, self.config)
        backend = self._load_backend(strategy, self.config["redirect_uri"])
        response = do_disconnect(backend, trans.user, association_id)
        if isinstance(response, str):
            return True, "", response
        return response.get("success", False), response.get("message", ""), ""

    def logout(self, trans, post_user_logout_href=None):
        """
        Logout from the identity provider.

        Constructs a logout URL using the OIDC end_session_endpoint if available.

        :param trans: Galaxy transaction object
        :param post_user_logout_href: URL to redirect to after logout
        :return: Logout redirect URI
        """
        on_the_fly_config(trans.sa_session)
        strategy = Strategy(trans.request, trans.session, Storage, self.config)
        backend = self._load_backend(strategy, self.config["redirect_uri"])

        # Get OIDC configuration to find end_session_endpoint
        try:
            oidc_config = backend.oidc_config()
            end_session_endpoint = oidc_config.get("end_session_endpoint")

            if end_session_endpoint:
                # Construct logout URL with optional post_logout_redirect_uri
                if post_user_logout_href:
                    logout_url = f"{end_session_endpoint}?post_logout_redirect_uri={quote(post_user_logout_href)}"
                else:
                    logout_url = end_session_endpoint

                return logout_url
            else:
                # No end_session_endpoint available
                log.warning(f"No end_session_endpoint found in OIDC configuration for {self.config['provider']}")
                return post_user_logout_href or "/"

        except Exception as e:
            log.exception(f"Error getting logout URL for {self.config['provider']}: {e}")
            return post_user_logout_href or "/"

    def decode_user_access_token(self, sa_session, access_token):
        """
        Verifies and decodes an access token against this provider, returning the user and
        a dict containing the decoded token data.

        This is used for API authentication with Bearer tokens.

        :param sa_session: SQLAlchemy database session
        :param access_token: An OIDC access token
        :return: A tuple containing the user and decoded jwt data, or (None, None) if token is for different provider
        :rtype: Tuple[User, dict]
        :raises Exception: If token is valid but user hasn't logged in, or token validation fails
        """
        try:
            on_the_fly_config(sa_session)
            # Create a minimal strategy and backend just for token verification
            strategy = Strategy(None, {}, Storage, self.config)
            backend = self._load_backend(strategy, self.config["redirect_uri"])

            # Decode and verify the access token using the helper function
            # This will raise exceptions for: expired tokens, invalid audience, invalid signature, etc.
            decoded_jwt = _decode_access_token_helper(access_token, backend)

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

    def create_user(self, token, trans, login_redirect_url):
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

    def redirect(self, url):
        return url

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


def contains_required_data(response=None, is_new=False, **kwargs):
    """
    This function is called as part of authentication and authorization
    pipeline before user is authenticated or authorized (see AUTH_PIPELINE).

    This function asserts if all the data required by Galaxy for a user
    is provided. It raises an exception if any of the required data is missing,
    and returns void if otherwise.

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

    :param kwargs:      may contain the following keys among others:

                        -   uid:        user ID
                        -   user:       Galaxy user; if user is already authenticated
                        -   backend:    the backend that is used for user authentication.
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
    if not response.get("id_token"):
        # This can happen if a non-OIDC compliant backend is used;
        # e.g., an OAuth2.0-based backend that only generates access token.
        raise MalformedContents(err_msg=f"Missing identity token. {hint_msg}")
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


def decode_access_token(social: UserAuthnzToken, backend: OpenIdConnectAuth, **kwargs):
    """
    Auth pipeline step to decode the OIDC access token, if possible.
    Note that some OIDC providers return an opaque access token, which
    cannot be decoded.

    Returns the access token, making it available as a new argument
    "access_token" that can be used in future pipeline steps. If
    decoding the access token is not possible, access_token will be None.

    Depends on "access_token" being present in social.extra_data,
    which should be handled by social_core.pipeline.social_auth.load_extra_data, so
    this step should be placed after load_extra_data in the pipeline.
    """
    if social.extra_data is None:
        return {"access_token": None}
    access_token_encoded = social.extra_data.get("access_token")
    if access_token_encoded is None:
        return {"access_token": None}
    if not _is_decodable_jwt(access_token_encoded):
        log.warning(
            "Access token is not in header.payload.signature format and can't be decoded (may be an opaque token)"
        )
        return {"access_token": None}
    try:
        access_token_data = _decode_access_token_helper(token_str=access_token_encoded, backend=backend)
    except InvalidTokenError as e:
        log.warning(f"Access token couldn't be decoded: {e}")
        return {"access_token": None}
    return {"access_token": access_token_data}


def _is_decodable_jwt(token_str: str) -> bool:
    """
    Check if a token string looks like a decodable JWT.
    We assume decodable JWTs are in the format header.payload.signature
    """
    components = token_str.split(".")
    return len(components) == 3


def _decode_access_token_helper(token_str: str, backend: OpenIdConnectAuth) -> dict:
    """
    Decode the access token (verifying that signature, expiry and
    audience are valid).

    Requires accepted_audiences to be configured in the OIDC backend config
    """
    signing_key = backend.find_valid_key(token_str)
    jwk = jwt.PyJWK(signing_key)
    decoded = jwt.decode(
        token_str,
        key=jwk,
        algorithms=[jwk.algorithm_name],
        audience=backend.strategy.config["accepted_audiences"],
        issuer=backend.id_token_issuer(),
        options={
            "verify_signature": True,
            "verify_exp": True,
            "verify_nbf": True,
            "verify_iat": True,
            "verify_aud": bool(backend.strategy.config["accepted_audiences"]),
            "verify_iss": True,
        },
    )
    return decoded


def associate_by_email_if_logged_in(
    strategy=None, backend=None, details=None, user=None, is_new=False, *args, **kwargs
):
    """
    Custom pipeline step to handle email-based account association.

    This replaces social_core.pipeline.social_auth.associate_by_email with Galaxy-specific logic:
    - If user is currently logged in (passed from trans.user): auto-associate the OIDC identity
    - If user is NOT logged in but an account with that email exists:
      - If fixed_delegated_auth is enabled: auto-associate with existing user
      - Otherwise: prompt for confirmation
    - If no account exists: continue with user creation

    Returns a dict with 'user' if association happened, or a redirect URL to stop the pipeline.
    """
    if user:
        # User is already logged in (from trans.user in callback) or was found by social_user step
        # In either case, we can proceed with association
        return

    email = details.get("email")
    if not email:
        # No email to match, continue with user creation
        return

    # User is not logged in - check if an account with this email exists
    sa_session = UserAuthnzToken.sa_session
    existing_user = sa_session.query(User).where(func.lower(User.email) == email.lower()).first()

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
            sa_session = UserAuthnzToken.sa_session
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


def set_redirect_url(
    strategy=None, backend=None, details=None, user=None, is_new=False, social=None, **kwargs
):
    """
    Custom pipeline step to set the redirect URL based on context.

    This mirrors the custos implementation's redirect logic:
    - If fixed_delegated_auth is enabled: redirect to root (LOGIN_REDIRECT_URL)
    - Otherwise: redirect to user/external_ids with appropriate parameters

    This should be the last step in the pipeline, after the user has been created/associated.
    """
    login_redirect_url = strategy.config.get(setting_name("LOGIN_REDIRECT_URL"), "/")
    fixed_delegated_auth = strategy.config.get("FIXED_DELEGATED_AUTH", False)

    if fixed_delegated_auth:
        # For fixed_delegated_auth, redirect to the base URL without extra parameters
        strategy.session_set("next", login_redirect_url)
    else:
        # Default: redirect to user/external_ids
        # The callback method will add the notification message
        strategy.session_set("next", f"{login_redirect_url}user/external_ids")

    return
