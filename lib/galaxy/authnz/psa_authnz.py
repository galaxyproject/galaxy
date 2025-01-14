import json
import logging
import time

import jwt
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
from sqlalchemy.exc import IntegrityError

from galaxy.exceptions import MalformedContents
from galaxy.model import (
    PSAAssociation,
    PSACode,
    PSANonce,
    PSAPartial,
    UserAuthnzToken,
)
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    requests,
)
from . import IdentityProvider

log = logging.getLogger(__name__)

# key: a component name which PSA requests.
# value: is the name of a class associated with that key.
DEFAULTS = {"STRATEGY": "Strategy", "STORAGE": "Storage"}

BACKENDS = {
    "google": "social_core.backends.google_openidconnect.GoogleOpenIdConnect",
    "globus": "social_core.backends.globus.GlobusOpenIdConnect",
    "elixir": "social_core.backends.elixir.ElixirOpenIdConnect",
    "okta": "social_core.backends.okta_openidconnect.OktaOpenIdConnect",
    "azure": "social_core.backends.azuread_tenant.AzureADV2TenantOAuth2",
    "egi_checkin": "social_core.backends.egi_checkin.EGICheckinOpenIdConnect",
    "oidc": "social_core.backends.open_id_connect.OpenIdConnectAuth",
}

BACKENDS_NAME = {
    "google": "google-openidconnect",
    "globus": "globus",
    "elixir": "elixir",
    "okta": "okta-openidconnect",
    "azure": "azuread-v2-tenant-oauth2",
    "egi_checkin": "egi-checkin",
    "oidc": "oidc",
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
    # Associates the current social details with another user account with
    # a similar email address.
    "social_core.pipeline.social_auth.associate_by_email",
    # Create a user account if we haven't found one yet.
    "social_core.pipeline.user.create_user",
    # Create the record that associated the social account with this user.
    "social_core.pipeline.social_auth.associate_user",
    # Populate the extra_data field in the social record with the values
    # specified by settings (and the default ones like access_token, etc).
    "social_core.pipeline.social_auth.load_extra_data",
    # Update the user record with any changed info from the auth service.
    "social_core.pipeline.user.user_details",
)

DISCONNECT_PIPELINE = ("galaxy.authnz.psa_authnz.allowed_to_disconnect", "galaxy.authnz.psa_authnz.disconnect")


class PSAAuthnz(IdentityProvider):
    def __init__(self, provider, oidc_config, oidc_backend_config):
        self.config = {"provider": provider.lower()}
        for key, value in oidc_config.items():
            self.config[setting_name(key)] = value

        self.config[setting_name("USER_MODEL")] = "models.User"
        self.config["SOCIAL_AUTH_PIPELINE"] = AUTH_PIPELINE
        self.config["DISCONNECT_PIPELINE"] = DISCONNECT_PIPELINE
        self.config[setting_name("AUTHENTICATION_BACKENDS")] = (BACKENDS[provider],)

        self.config["VERIFY_SSL"] = oidc_config.get("VERIFY_SSL")
        self.config["REQUESTS_TIMEOUT"] = oidc_config.get("REQUESTS_TIMEOUT")
        self.config["ID_TOKEN_MAX_AGE"] = oidc_config.get("ID_TOKEN_MAX_AGE")

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
        self.config["EXTRA_SCOPES"] = oidc_backend_config.get("extra_scopes")
        if oidc_backend_config.get("oidc_endpoint"):
            self.config["OIDC_ENDPOINT"] = oidc_backend_config["oidc_endpoint"]
        if oidc_backend_config.get("prompt") is not None:
            self.config[setting_name("AUTH_EXTRA_ARGUMENTS")]["prompt"] = oidc_backend_config.get("prompt")
        if oidc_backend_config.get("api_url") is not None:
            self.config[setting_name("API_URL")] = oidc_backend_config.get("api_url")
        if oidc_backend_config.get("url") is not None:
            self.config[setting_name("URL")] = oidc_backend_config.get("url")

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
        if not user_authnz_token or not user_authnz_token.extra_data:
            return False
        # refresh tokens if they reached their half lifetime
        if "expires" in user_authnz_token.extra_data:
            expires = user_authnz_token.extra_data["expires"]
        elif "expires_in" in user_authnz_token.extra_data:
            expires = user_authnz_token.extra_data["expires_in"]
        else:
            log.debug("No `expires` or `expires_in` key found in token extra data, cannot refresh")
            return False
        if int(user_authnz_token.extra_data["auth_time"]) + int(expires) / 2 <= int(time.time()):
            on_the_fly_config(trans.sa_session)
            if self.config["provider"] == "azure":
                self.refresh_azure(user_authnz_token)
            else:
                strategy = Strategy(trans.request, trans.session, Storage, self.config)
                user_authnz_token.refresh_token(strategy)
            return True
        return False

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

        return redirect_url, self.config.get("user", None)

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

    def start(self):
        self.clean_partial_pipeline()
        if self.backend.uses_redirect():
            return self.redirect(self.backend.auth_url())
        else:
            return self.html(self.backend.auth_html())

    def complete(self, *args, **kwargs):
        return self.backend.auth_complete(*args, **kwargs)

    def continue_pipeline(self, *args, **kwargs):
        return self.backend.continue_pipeline(*args, **kwargs)


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
