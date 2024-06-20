import base64
import hashlib
import json
import logging
import os
from datetime import (
    datetime,
    timedelta,
)
from urllib.parse import quote

import jwt
import requests
from oauthlib.common import generate_nonce
from requests_oauthlib import OAuth2Session

from galaxy import (
    exceptions,
    util,
)
from galaxy.model import (
    CustosAuthnzToken,
    User,
)
from galaxy.model.orm.util import add_object_to_object_session
from . import IdentityProvider

try:
    import pkce
except ImportError:
    pkce = None  # type: ignore[assignment]

log = logging.getLogger(__name__)
STATE_COOKIE_NAME = "galaxy-oidc-state"
NONCE_COOKIE_NAME = "galaxy-oidc-nonce"
VERIFIER_COOKIE_NAME = "galaxy-oidc-verifier"
KEYCLOAK_BACKENDS = {"custos", "cilogon", "keycloak"}


class InvalidAuthnzConfigException(Exception):
    pass


class CustosAuthnz(IdentityProvider):
    def __init__(self, provider, oidc_config, oidc_backend_config, idphint=None):
        provider = provider.lower()
        self.config = {"provider": provider}
        self.config["verify_ssl"] = oidc_config["VERIFY_SSL"]
        self.config["url"] = oidc_backend_config["url"]
        self.config["client_id"] = oidc_backend_config["client_id"]
        self.config["client_secret"] = oidc_backend_config["client_secret"]
        self.config["redirect_uri"] = oidc_backend_config["redirect_uri"]
        self.config["ca_bundle"] = oidc_backend_config.get("ca_bundle", None)
        self.config["pkce_support"] = oidc_backend_config.get("pkce_support", False)
        self.config["extra_params"] = {
            "kc_idp_hint": oidc_backend_config.get(
                "idphint", "oidc" if self.config["provider"] in ["custos", "keycloak"] else "cilogon"
            )
        }
        if provider == "cilogon":
            self._load_config_for_cilogon()
        elif provider == "custos":
            self._load_config_for_custos()
        elif provider == "keycloak":
            self._load_config_for_keycloak()

    def _decode_token_no_signature(self, token):
        return jwt.decode(token, audience=self.config["client_id"], options={"verify_signature": False})

    def authenticate(self, trans, idphint=None):
        base_authorize_url = self.config["authorization_endpoint"]
        scopes = ["openid", "email", "profile"]
        if self.config["provider"] in ["custos", "cilogon"]:
            scopes.append("org.cilogon.userinfo")
        oauth2_session = self._create_oauth2_session(scope=scopes)
        nonce = generate_nonce()
        nonce_hash = self._hash_nonce(nonce)
        extra_params = {"nonce": nonce_hash}
        if idphint is not None:
            extra_params["idphint"] = idphint
        if self.config["pkce_support"]:
            if not pkce:
                raise InvalidAuthnzConfigException(
                    "The python 'pkce' library is not installed but Galaxy is configured to use it "
                    "(see oidc_backends_config).  Make sure pkce is installed correctly to proceed."
                )
            code_verifier, code_challenge = pkce.generate_pkce_pair(96)
            extra_params["code_challenge"] = code_challenge
            extra_params["code_challenge_method"] = "S256"
            trans.set_cookie(value=code_verifier, name=VERIFIER_COOKIE_NAME)
        if "extra_params" in self.config:
            extra_params.update(self.config["extra_params"])
        authorization_url, state = oauth2_session.authorization_url(base_authorize_url, **extra_params)
        trans.set_cookie(value=state, name=STATE_COOKIE_NAME)
        trans.set_cookie(value=nonce, name=NONCE_COOKIE_NAME)
        return authorization_url

    def callback(self, state_token, authz_code, trans, login_redirect_url):
        # Take state value to validate from token. OAuth2Session.fetch_token
        # will validate that the state query parameter value on the URL matches
        # this value.
        state_cookie = trans.get_cookie(name=STATE_COOKIE_NAME)
        oauth2_session = self._create_oauth2_session(state=state_cookie)
        token = self._fetch_token(oauth2_session, trans)
        access_token = token["access_token"]
        id_token = token["id_token"]
        refresh_token = token["refresh_token"] if "refresh_token" in token else None
        expiration_time = datetime.now() + timedelta(seconds=token.get("expires_in", 3600))
        refresh_expiration_time = (
            (datetime.now() + timedelta(seconds=token["refresh_expires_in"])) if "refresh_expires_in" in token else None
        )

        # Get nonce from token['id_token'] and validate. 'nonce' in the
        # id_token is a hash of the nonce stored in the NONCE_COOKIE_NAME
        # cookie.
        id_token_decoded = self._decode_token_no_signature(id_token)
        nonce_hash = id_token_decoded["nonce"]
        self._validate_nonce(trans, nonce_hash)

        # Get userinfo and lookup/create Galaxy user record
        if id_token_decoded.get("email", None):
            userinfo = id_token_decoded
        else:
            userinfo = self._get_userinfo(oauth2_session)
        email = userinfo["email"]
        user_id = userinfo["sub"]

        # Create or update custos_authnz_token record
        custos_authnz_token = self._get_custos_authnz_token(trans.sa_session, user_id, self.config["provider"])
        if custos_authnz_token is None:
            user = trans.user
            if not user:
                existing_user = trans.sa_session.query(User).filter_by(email=email).first()
                if existing_user:
                    # If there is only a single external authentication
                    # provider in use, trust the user provided and
                    # automatically associate.
                    # TODO: Future work will expand on this and provide an
                    # interface for when there are multiple auth providers
                    # allowing explicit authenticated association.
                    if (
                        trans.app.config.enable_oidc
                        and len(trans.app.config.oidc) == 1
                        and len(trans.app.auth_manager.authenticators) == 0
                    ):
                        user = existing_user
                    else:
                        message = f"There already exists a user with email {email}.  To associate this external login, you must first be logged in as that existing account."
                        log.exception(message)
                        raise exceptions.AuthenticationFailed(message)
                elif self.config["provider"] == "custos":
                    login_redirect_url = f"{login_redirect_url}root/login?confirm=true&custos_token={json.dumps(token)}"
                    return login_redirect_url, None
                else:
                    username = self._username_from_userinfo(trans, userinfo)
                    user = trans.app.user_manager.create(email=email, username=username)
                    if trans.app.config.user_activation_on:
                        trans.app.user_manager.send_activation_email(trans, email, username)

            custos_authnz_token = CustosAuthnzToken(
                user=user,
                external_user_id=user_id,
                provider=self.config["provider"],
                access_token=access_token,
                id_token=id_token,
                refresh_token=refresh_token,
                expiration_time=expiration_time,
                refresh_expiration_time=refresh_expiration_time,
            )
        else:
            custos_authnz_token.access_token = access_token
            custos_authnz_token.id_token = id_token
            custos_authnz_token.refresh_token = refresh_token
            custos_authnz_token.expiration_time = expiration_time
            custos_authnz_token.refresh_expiration_time = refresh_expiration_time
        trans.sa_session.add(custos_authnz_token)
        trans.sa_session.flush()
        return "/", custos_authnz_token.user

    def create_user(self, token, trans, login_redirect_url):
        token_dict = json.loads(token)

        access_token = token_dict["access_token"]
        id_token = token_dict["id_token"]
        refresh_token = token_dict["refresh_token"] if "refresh_token" in token_dict else None
        expiration_time = datetime.now() + timedelta(
            seconds=token_dict.get("expires_in", 3600)
        )  # might be a problem cause times no long valid
        refresh_expiration_time = (
            (datetime.now() + timedelta(seconds=token_dict["refresh_expires_in"]))
            if "refresh_expires_in" in token_dict
            else None
        )

        # Get nonce from token['id_token'] and validate. 'nonce' in the
        # id_token is a hash of the nonce stored in the NONCE_COOKIE_NAME
        # cookie.
        userinfo = self._decode_token_no_signature(id_token)

        # Get userinfo and create Galaxy user record
        email = userinfo["email"]
        # Check if username if already taken
        username = self._username_from_userinfo(trans, userinfo)
        user_id = userinfo["sub"]

        user = trans.app.user_manager.create(email=email, username=username)
        if trans.app.config.user_activation_on:
            trans.app.user_manager.send_activation_email(trans, email, username)

        custos_authnz_token = CustosAuthnzToken(
            external_user_id=user_id,
            provider=self.config["provider"],
            access_token=access_token,
            id_token=id_token,
            refresh_token=refresh_token,
            expiration_time=expiration_time,
            refresh_expiration_time=refresh_expiration_time,
        )
        add_object_to_object_session(custos_authnz_token, user)
        custos_authnz_token.user = user

        trans.sa_session.add(user)
        trans.sa_session.add(custos_authnz_token)
        trans.sa_session.flush()
        return login_redirect_url, user

    def disconnect(self, provider, trans, email=None, disconnect_redirect_url=None):
        try:
            user = trans.user
            index = 0
            # Find CustosAuthnzToken record for this provider (should only be one)
            provider_tokens = [token for token in user.custos_auth if token.provider == self.config["provider"]]
            if len(provider_tokens) == 0:
                raise Exception(f"User is not associated with provider {self.config['provider']}")
            if len(provider_tokens) > 1:
                for idx, token in enumerate(provider_tokens):
                    id_token_decoded = self._decode_token_no_signature(token.id_token)
                    if id_token_decoded["email"] == email:
                        index = idx
            trans.sa_session.delete(provider_tokens[index])
            trans.sa_session.flush()
            return True, "", disconnect_redirect_url
        except Exception as e:
            return False, f"Failed to disconnect provider {provider}: {util.unicodify(e)}", None

    def logout(self, trans, post_user_logout_href=None):
        try:
            redirect_url = self.config["end_session_endpoint"]
            if post_user_logout_href is not None:
                redirect_url += f"?redirect_uri={quote(post_user_logout_href)}"
            return redirect_url
        except Exception as e:
            log.error("Failed to generate logout redirect_url", exc_info=e)
            return None

    def _create_oauth2_session(self, state=None, scope=None):
        client_id = self.config["client_id"]
        redirect_uri = self.config["redirect_uri"]
        if redirect_uri.startswith("http://localhost") and os.environ.get("OAUTHLIB_INSECURE_TRANSPORT", None) != "1":
            log.warning("Setting OAUTHLIB_INSECURE_TRANSPORT to '1' to allow plain HTTP (non-SSL) callback")
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        session = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri, state=state)
        session.verify = self._get_verify_param()
        return session

    def _fetch_token(self, oauth2_session, trans):
        if self.config.get("iam_client_secret"):
            # Custos uses the Keycloak client secret to get the token
            client_secret = self.config["iam_client_secret"]
        else:
            client_secret = self.config["client_secret"]
        token_endpoint = self.config["token_endpoint"]
        clientIdAndSec = f"{self.config['client_id']}:{self.config['client_secret']}"  # for custos

        params = {
            "client_secret": client_secret,
            "authorization_response": trans.request.url,
            "headers": {
                "Authorization": f"Basic {util.unicodify(base64.b64encode(util.smart_str(clientIdAndSec)))}"
            },  # for custos
            "verify": self._get_verify_param(),
        }
        if self.config["pkce_support"]:
            code_verifier = trans.get_cookie(name=VERIFIER_COOKIE_NAME)
            trans.set_cookie("", name=VERIFIER_COOKIE_NAME, age=-1)
            params["code_verifier"] = code_verifier
        return oauth2_session.fetch_token(token_endpoint, **params)

    def _get_userinfo(self, oauth2_session):
        userinfo_endpoint = self.config["userinfo_endpoint"]
        return oauth2_session.get(userinfo_endpoint, verify=self._get_verify_param()).json()

    def _get_custos_authnz_token(self, sa_session, user_id, provider):
        return sa_session.query(CustosAuthnzToken).filter_by(external_user_id=user_id, provider=provider).one_or_none()

    def _hash_nonce(self, nonce):
        return hashlib.sha256(util.smart_str(nonce)).hexdigest()

    def _validate_nonce(self, trans, nonce_hash):
        nonce_cookie = trans.get_cookie(name=NONCE_COOKIE_NAME)
        # Delete the nonce cookie
        trans.set_cookie("", name=NONCE_COOKIE_NAME, age=-1)
        nonce_cookie_hash = self._hash_nonce(nonce_cookie)
        if nonce_hash != nonce_cookie_hash:
            raise Exception("Nonce mismatch. Check that configured redirect_uri matches the URL you are using.")

    def _load_config_for_cilogon(self):
        # Set cilogon endpoints
        self.config["authorization_endpoint"] = "https://cilogon.org/authorize"
        self.config["token_endpoint"] = "https://cilogon.org/oauth2/token"
        self.config["userinfo_endpoint"] = "https://cilogon.org/oauth2/userinfo"

    def _load_config_for_custos(self):
        self.config["well_known_oidc_config_uri"] = self._get_well_known_uri_from_url(self.config["provider"])
        self.config["credential_url"] = f"{self.config['url'].rstrip('/')}/credentials"
        self._get_custos_credentials()
        # Set custos endpoints
        clientIdAndSec = f"{self.config['client_id']}:{self.config['client_secret']}"
        eps = requests.get(
            self.config["well_known_oidc_config_uri"],
            headers={"Authorization": f"Basic {util.unicodify(base64.b64encode(util.smart_str(clientIdAndSec)))}"},
            verify=False,
            params={"client_id": self.config["client_id"]},
            timeout=util.DEFAULT_SOCKET_TIMEOUT,
        )
        well_known_oidc_config = eps.json()
        self._load_well_known_oidc_config(well_known_oidc_config)

    def _load_config_for_keycloak(self):
        self.config["well_known_oidc_config_uri"] = self._get_well_known_uri_from_url(self.config["provider"])
        well_known_oidc_config = self._fetch_well_known_oidc_config(self.config["well_known_oidc_config_uri"])
        self._load_well_known_oidc_config(well_known_oidc_config)

    def _get_custos_credentials(self):
        clientIdAndSec = f"{self.config['client_id']}:{self.config['client_secret']}"
        creds = requests.get(
            self.config["credential_url"],
            headers={"Authorization": f"Basic {util.unicodify(base64.b64encode(util.smart_str(clientIdAndSec)))}"},
            verify=False,
            params={"client_id": self.config["client_id"]},
            timeout=util.DEFAULT_SOCKET_TIMEOUT,
        )
        credentials = creds.json()
        self.config["iam_client_secret"] = credentials["iam_client_secret"]

    def _get_well_known_uri_from_url(self, provider):
        # TODO: Look up this URL from a Python library
        if provider in ["custos", "keycloak"]:
            base_url = self.config["url"]
            # Remove potential trailing slash to avoid "//realms"
            base_url = base_url if base_url[-1] != "/" else base_url[:-1]
            return f"{base_url}/.well-known/openid-configuration"
        else:
            raise Exception(f"Unknown Custos provider name: {provider}")

    def _fetch_well_known_oidc_config(self, well_known_uri):
        try:
            return requests.get(
                well_known_uri, verify=self._get_verify_param(), timeout=util.DEFAULT_SOCKET_TIMEOUT
            ).json()
        except Exception:
            log.error(f"Failed to load well-known OIDC config URI: {well_known_uri}")
            raise

    def _load_well_known_oidc_config(self, well_known_oidc_config):
        self.config["authorization_endpoint"] = well_known_oidc_config["authorization_endpoint"]
        self.config["token_endpoint"] = well_known_oidc_config["token_endpoint"]
        self.config["userinfo_endpoint"] = well_known_oidc_config["userinfo_endpoint"]
        self.config["end_session_endpoint"] = well_known_oidc_config.get("end_session_endpoint")

    def _get_verify_param(self):
        """Return 'ca_bundle' if 'verify_ssl' is true and 'ca_bundle' is configured."""
        # in requests_oauthlib, the verify param can either be a boolean or a CA bundle path
        if self.config["ca_bundle"] is not None and self.config["verify_ssl"]:
            return self.config["ca_bundle"]
        else:
            return self.config["verify_ssl"]

    def _username_from_userinfo(self, trans, userinfo):
        username = userinfo.get("preferred_username", userinfo["email"])
        if "@" in username:
            username = username.split("@")[0]  # username created from username portion of email
        username = util.ready_name_for_url(username).lower()
        if trans.sa_session.query(trans.app.model.User).filter_by(username=username).first():
            # if username already exists in database, append integer and iterate until unique username found
            count = 0
            while trans.sa_session.query(trans.app.model.User).filter_by(username=(f"{username}{count}")).first():
                count += 1
            return f"{username}{count}"
        else:
            return username
