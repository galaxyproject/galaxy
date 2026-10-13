import base64
import hashlib
import logging
import os
import time
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    Optional,
)
from urllib.parse import (
    quote,
    urlencode,
)

import jwt
from oauthlib.common import generate_nonce
from requests_oauthlib import OAuth2Session
from sqlalchemy import func

from galaxy import (
    exceptions,
    util,
)
from galaxy.model import (
    CustosAuthnzToken,
    User,
)
from galaxy.util import requests
from galaxy.web import url_for
from . import IdentityProvider
from .flow_state import (
    authentication_id,
    FlowState,
    InvalidFlow,
)

try:
    import pkce
except ImportError:
    pkce = None  # type: ignore[assignment, unused-ignore]

log = logging.getLogger(__name__)
KEYCLOAK_BACKENDS = {"custos", "cilogon", "keycloak"}


class InvalidAuthnzConfigException(Exception):
    pass


@dataclass
class CustosAuthnzConfiguration:
    provider: str
    verify_ssl: Optional[bool]
    url: str
    label: str
    client_id: str
    client_secret: str
    require_create_confirmation: bool
    redirect_uri: str
    ca_bundle: Optional[str]
    pkce_support: bool
    accepted_audiences: list[str]
    extra_params: Optional[dict]
    extra_scopes: list[str]
    authorization_endpoint: Optional[str]
    token_endpoint: Optional[str]
    end_session_endpoint: Optional[str]
    well_known_oidc_config_uri: Optional[str]
    iam_client_secret: Optional[str]
    userinfo_endpoint: Optional[str]
    credential_url: Optional[str]
    issuer: Optional[str]
    jwks_uri: Optional[str]


class OIDCAuthnzBase(IdentityProvider):
    def __init__(self, provider, oidc_config, oidc_backend_config, idphint=None):
        provider = provider.lower()
        self.jwks_client: Optional[jwt.PyJWKClient]
        self.config = CustosAuthnzConfiguration(
            provider=provider,
            verify_ssl=oidc_config["VERIFY_SSL"],
            url=oidc_backend_config["url"],
            label=oidc_backend_config.get("label", provider.capitalize()),
            client_id=oidc_backend_config["client_id"],
            client_secret=oidc_backend_config["client_secret"],
            require_create_confirmation=oidc_backend_config.get("require_create_confirmation", provider == "custos"),
            redirect_uri=oidc_backend_config["redirect_uri"],
            ca_bundle=oidc_backend_config.get("ca_bundle", None),
            pkce_support=oidc_backend_config.get("pkce_support", False),
            accepted_audiences=list(
                filter(
                    None,
                    map(
                        str.strip,
                        oidc_backend_config.get("accepted_audiences", oidc_backend_config["client_id"]).split(","),
                    ),
                )
            ),
            extra_params={},
            extra_scopes=oidc_backend_config.get("extra_scopes", []),
            authorization_endpoint=None,
            token_endpoint=None,
            end_session_endpoint=None,
            well_known_oidc_config_uri=None,
            iam_client_secret=None,
            userinfo_endpoint=None,
            credential_url=None,
            issuer=None,
            jwks_uri=None,
        )

    def _decode_token_no_signature(self, token):
        return jwt.decode(token, audience=self.config.client_id, options={"verify_signature": False})

    def refresh(self, trans, custos_authnz_token):
        if custos_authnz_token is None:
            raise exceptions.AuthenticationFailed("cannot find authorized user while refreshing token")
        id_token_decoded = self._decode_token_no_signature(custos_authnz_token.id_token)
        # do not refresh tokens if the id_token didn't reach its half-life
        if int(id_token_decoded["iat"]) + int(id_token_decoded["exp"]) > 2 * int(time.time()):
            return False
        if not custos_authnz_token.refresh_token:
            return False

        # Try to extract expiration date from the refresh token. If expired, do not refresh token.
        try:
            refresh_token_decoded = self._decode_token_no_signature(custos_authnz_token.refresh_token)
            # do not attempt to use refresh token that is already expired
            if int(refresh_token_decoded["exp"]) <= int(time.time()):
                # in the future we might want to log out the user here
                return False
        except jwt.exceptions.DecodeError:
            log.warning("Refresh token cannot be decoded. Galaxy does not support non-decodable refresh tokens.")
            # If the refresh token is non-decodable, we do not use it because we cannot reliably determine its expiration date. See discussion in https://github.com/galaxyproject/galaxy/pull/20821
            return False

        oauth2_session = self._create_oauth2_session()
        token_endpoint = self.config.token_endpoint
        if self.config.iam_client_secret:
            client_secret = self.config.iam_client_secret
        else:
            client_secret = self.config.client_secret
        clientIdAndSec = f"{self.config.client_id}:{self.config.client_secret}"  # for custos

        params = {
            "client_id": self.config.client_id,
            "client_secret": client_secret,
            "refresh_token": custos_authnz_token.refresh_token,
            "headers": {
                "Authorization": f"Basic {util.unicodify(base64.b64encode(util.smart_str(clientIdAndSec)))}"
            },  # for custos
        }

        token = oauth2_session.refresh_token(token_endpoint, **params)
        processed_token = self._process_token(trans, oauth2_session, token, False)

        custos_authnz_token.access_token = processed_token["access_token"]
        custos_authnz_token.id_token = processed_token["id_token"]
        custos_authnz_token.refresh_token = processed_token["refresh_token"]
        custos_authnz_token.expiration_time = processed_token["expiration_time"]
        custos_authnz_token.refresh_expiration_time = processed_token["refresh_expiration_time"]

        trans.sa_session.add(custos_authnz_token)
        trans.sa_session.flush()
        return True

    def _get_provider_specific_scopes(self):
        return []

    def authenticate(self, trans, idphint=None):
        base_authorize_url = self.config.authorization_endpoint
        scopes = ["openid", "email", "profile"]
        scopes.extend(self.config.extra_scopes)
        scopes.extend(self._get_provider_specific_scopes())
        oauth2_session = self._create_oauth2_session(scope=scopes)
        nonce = generate_nonce()
        nonce_hash = self._hash_nonce(nonce)
        extra_params = {"nonce": nonce_hash}
        code_verifier = None
        if idphint is not None:
            extra_params["idphint"] = idphint
        if self.config.pkce_support:
            if not pkce:
                raise InvalidAuthnzConfigException(
                    "The python 'pkce' library is not installed but Galaxy is configured to use it "
                    "(see oidc_backends_config).  Make sure pkce is installed correctly to proceed."
                )
            code_verifier, code_challenge = pkce.generate_pkce_pair(96)
            extra_params["code_challenge"] = code_challenge
            extra_params["code_challenge_method"] = "S256"
        if self.config.extra_params:
            extra_params.update(self.config.extra_params)
        authorization_url, state = oauth2_session.authorization_url(base_authorize_url, **extra_params)
        FlowState(trans.sa_session, trans.galaxy_session, self.config.provider).save(
            "authentication", {"nonce": nonce_hash, "code_verifier": code_verifier}, identifier=authentication_id(state)
        )
        return authorization_url

    def _process_token(self, trans, oauth2_session, token, validate_nonce=True, nonce=None):
        processed_token = {}
        processed_token["access_token"] = token["access_token"]
        processed_token["id_token"] = token["id_token"]
        processed_token["refresh_token"] = token["refresh_token"] if "refresh_token" in token else None
        processed_token["expiration_time"] = datetime.now() + timedelta(seconds=token.get("expires_in", 3600))
        processed_token["refresh_expiration_time"] = (
            (datetime.now() + timedelta(seconds=token["refresh_expires_in"])) if "refresh_expires_in" in token else None
        )

        # Tokens come directly from the configured token endpoint after a bound
        # authorization-code exchange. Validate claims here, never at confirmation.
        if validate_nonce:
            if not self.config.issuer:
                raise InvalidFlow()
            id_token_decoded = jwt.decode(
                processed_token["id_token"],
                audience=self.config.client_id,
                issuer=self.config.issuer,
                options={
                    "verify_signature": False,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require": ["exp", "iat", "sub", "aud", "iss"],
                },
            )
            if not nonce or id_token_decoded.get("nonce") != nonce:
                raise InvalidFlow()
            if id_token_decoded.get("azp", self.config.client_id) != self.config.client_id:
                raise InvalidFlow()
        else:
            id_token_decoded = self._decode_token_no_signature(processed_token["id_token"])
        if not isinstance(id_token_decoded["sub"], str) or not id_token_decoded["sub"]:
            raise InvalidFlow()
        if id_token_decoded.get("email"):
            userinfo = id_token_decoded
        else:
            userinfo = self._get_userinfo(oauth2_session)
            if userinfo.get("sub") != id_token_decoded["sub"]:
                raise InvalidFlow()
        if not isinstance(userinfo.get("email"), str) or not userinfo["email"]:
            raise InvalidFlow()
        processed_token["identity_expires_at"] = id_token_decoded["exp"]
        processed_token["email"] = userinfo["email"]
        processed_token["user_id"] = userinfo["sub"]
        processed_token["username"] = self._username_from_userinfo(trans, userinfo)
        return processed_token

    def callback(self, state_token, authz_code, trans, login_redirect_url):
        flow_state = FlowState(trans.sa_session, trans.galaxy_session, self.config.provider)
        authentication = flow_state.consume("authentication", authentication_id(state_token))
        oauth2_session = self._create_oauth2_session(state=state_token)
        token = self._fetch_token(oauth2_session, trans, code_verifier=authentication.get("code_verifier"))
        processed_token = self._process_token(trans, oauth2_session, token, nonce=authentication.get("nonce"))

        user_id = processed_token["user_id"]
        email = processed_token["email"]
        username = processed_token["username"]
        access_token = processed_token["access_token"]
        id_token = processed_token["id_token"]
        refresh_token = processed_token["refresh_token"]
        expiration_time = processed_token["expiration_time"]
        refresh_expiration_time = processed_token["refresh_expiration_time"]

        # Create or update custos_authnz_token record
        custos_authnz_token = self._get_custos_authnz_token(trans.sa_session, user_id, self.config.provider)
        if custos_authnz_token is None:
            user = trans.user
            existing_user = trans.sa_session.query(User).where(func.lower(User.email) == email.lower()).first()
            if not user:
                if existing_user:
                    if trans.app.config.fixed_delegated_auth:
                        user = existing_user
                    else:
                        message = f"There already exists a user with email {email}. To associate this external login, you must first be logged in as that existing account."
                        log.info(message)
                        login_redirect_url = (
                            f"{login_redirect_url}login/start"
                            f"?connect_external_provider={self.config.provider}"
                            f"&connect_external_email={email}"
                            f"&connect_external_label={self.config.label}"
                        )
                        return login_redirect_url, None
                elif self.config.require_create_confirmation:
                    pending = dict(processed_token)
                    for key in ("expiration_time", "refresh_expiration_time"):
                        pending[key] = pending[key].isoformat() if pending[key] else None
                    confirmation_id = flow_state.save(
                        "confirmation", pending, expires_at=processed_token["identity_expires_at"]
                    )
                    login_redirect_url = (
                        url_for("/login/start")
                        + "?"
                        + urlencode(
                            {"confirm": "true", "confirmation_id": confirmation_id, "provider": self.config.provider}
                        )
                    )
                    return login_redirect_url, None
                else:
                    user = trans.app.user_manager.create(email=email, username=username)
                    if trans.app.config.user_activation_on:
                        trans.app.user_manager.send_activation_email(trans, email, username)

            # Create a token to link this identity with an existing account
            custos_authnz_token = CustosAuthnzToken(
                user=user,
                external_user_id=user_id,
                provider=self.config.provider,
                access_token=access_token,
                id_token=id_token,
                refresh_token=refresh_token,
                expiration_time=expiration_time,
                refresh_expiration_time=refresh_expiration_time,
            )
            label = self.config.label
            if trans.app.config.fixed_delegated_auth:
                redirect_url = login_redirect_url
            elif existing_user and existing_user != user:
                redirect_url = (
                    f"{login_redirect_url}user/external_ids"
                    f"?email_exists={email}"
                    f"&notification=Your%20{label}%20identity%20has%20been%20linked"
                    "%20to%20your%20Galaxy%20account."
                )
            else:
                redirect_url = (
                    f"{login_redirect_url}user/external_ids"
                    f"?notification=Your%20{label}%20identity%20has%20been%20linked"
                    "%20to%20your%20Galaxy%20account."
                )
        else:
            # Identity is already linked to account - login as usual
            custos_authnz_token.access_token = access_token
            custos_authnz_token.id_token = id_token
            custos_authnz_token.refresh_token = refresh_token
            custos_authnz_token.expiration_time = expiration_time
            custos_authnz_token.refresh_expiration_time = refresh_expiration_time
            redirect_url = "/"

        trans.sa_session.add(custos_authnz_token)
        trans.sa_session.commit()

        return redirect_url, custos_authnz_token.user

    def create_user(self, confirmation_id, trans, login_redirect_url):
        data = self._consume_confirmation(confirmation_id, trans)
        email, user_id = data["email"], data["user_id"]
        if trans.sa_session.query(User).where(
            func.lower(User.email) == email.lower()
        ).first() or self._get_custos_authnz_token(trans.sa_session, user_id, self.config.provider):
            raise InvalidFlow()
        username = self._username_from_userinfo(trans, {"email": email, "preferred_username": data["username"]})
        user = trans.app.user_manager.create(email=email, username=username)
        if trans.app.config.user_activation_on:
            trans.app.user_manager.send_activation_email(trans, email, username)
        custos_authnz_token = CustosAuthnzToken(
            user=user,
            external_user_id=user_id,
            provider=self.config.provider,
            access_token=data["access_token"],
            id_token=data["id_token"],
            refresh_token=data["refresh_token"],
            expiration_time=datetime.fromisoformat(data["expiration_time"]),
            refresh_expiration_time=(
                datetime.fromisoformat(data["refresh_expiration_time"]) if data["refresh_expiration_time"] else None
            ),
        )
        trans.sa_session.add(custos_authnz_token)
        try:
            trans.sa_session.commit()
        except Exception:
            trans.sa_session.rollback()
            raise
        return login_redirect_url, user

    def cancel_user_creation(self, confirmation_id, trans):
        self._consume_confirmation(confirmation_id, trans)

    def _consume_confirmation(self, confirmation_id, trans):
        if not trans.app.config.enable_oidc or not self.config.require_create_confirmation or trans.user:
            raise InvalidFlow()
        return FlowState(trans.sa_session, trans.galaxy_session, self.config.provider).consume(
            "confirmation", confirmation_id
        )

    def disconnect(self, provider, trans, disconnect_redirect_url=None, email=None, association_id=None):
        try:
            user = trans.user
            index = 0
            # Find CustosAuthnzToken record for this provider (should only be one)
            provider_tokens = [token for token in user.custos_auth if token.provider == self.config.provider]
            if len(provider_tokens) == 0:
                raise Exception(f"User is not associated with provider {self.config.provider}")
            if len(provider_tokens) > 1:
                for idx, token in enumerate(provider_tokens):
                    id_token_decoded = self._decode_token_no_signature(token.id_token)
                    if id_token_decoded["email"] == email:
                        index = idx
            trans.sa_session.delete(provider_tokens[index])
            trans.sa_session.commit()
            return True, "", disconnect_redirect_url
        except Exception as e:
            return False, f"Failed to disconnect provider {provider}: {util.unicodify(e)}", None

    def logout(self, trans, post_user_logout_href=None):
        if not self.config.redirect_uri:
            log.error("Failed to generate logout redirect_url")
            return None
        try:
            if self.config.end_session_endpoint:
                redirect_url = self.config.end_session_endpoint
            if post_user_logout_href is not None:
                redirect_url += f"?redirect_uri={quote(post_user_logout_href)}"
            return redirect_url
        except Exception as e:
            log.error("Failed to generate logout redirect_url", exc_info=e)
            return None

    def _create_oauth2_session(self, state=None, scope=None):
        client_id = self.config.client_id
        redirect_uri = self.config.redirect_uri
        if redirect_uri.startswith("http://localhost") and os.environ.get("OAUTHLIB_INSECURE_TRANSPORT", None) != "1":
            log.warning("Setting OAUTHLIB_INSECURE_TRANSPORT to '1' to allow plain HTTP (non-SSL) callback")
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        session = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri, state=state)
        session.verify = self._get_verify_param()
        return session

    def _fetch_token(self, oauth2_session, trans, code_verifier=None):
        if self.config.iam_client_secret:
            # Custos uses the Keycloak client secret to get the token
            client_secret = self.config.iam_client_secret
        else:
            client_secret = self.config.client_secret
        token_endpoint = self.config.token_endpoint
        clientIdAndSec = f"{self.config.client_id}:{self.config.client_secret}"  # for custos

        params = {
            "client_secret": client_secret,
            "authorization_response": trans.request.url,
            "headers": {
                "Authorization": f"Basic {util.unicodify(base64.b64encode(util.smart_str(clientIdAndSec)))}"
            },  # for custos
            "verify": self._get_verify_param(),
        }
        if self.config.pkce_support:
            if not code_verifier:
                raise InvalidFlow()
            params["code_verifier"] = code_verifier
        return oauth2_session.fetch_token(token_endpoint, **params)

    def _get_userinfo(self, oauth2_session):
        userinfo_endpoint = self.config.userinfo_endpoint
        return oauth2_session.get(userinfo_endpoint, verify=self._get_verify_param()).json()

    @staticmethod
    def _get_custos_authnz_token(sa_session, user_id, provider):
        return sa_session.query(CustosAuthnzToken).filter_by(external_user_id=user_id, provider=provider).one_or_none()

    @staticmethod
    def _hash_nonce(nonce):
        return hashlib.sha256(util.smart_str(nonce)).hexdigest()

    def _load_config(self, headers: Optional[dict] = None, params: Optional[dict] = None):
        if not headers:
            headers = {}
        if not params:
            params = {}
        self.config.well_known_oidc_config_uri = self._get_well_known_uri_from_url(self.config.provider)
        if not self.config.well_known_oidc_config_uri:
            log.error(f"Failed to load well-known OIDC config URI: {self.config.well_known_oidc_config_uri}")
            raise Exception(f"Failed to load well-known OIDC config URI: {self.config.well_known_oidc_config_uri}")
        try:
            well_known_oidc_config = requests.get(
                self.config.well_known_oidc_config_uri,
                headers=headers,
                verify=self._get_verify_param(),
                timeout=util.DEFAULT_SOCKET_TIMEOUT,
                params=params,
            ).json()
            self._load_well_known_oidc_config(well_known_oidc_config)
        except Exception:
            log.error(f"Failed to load well-known OIDC config URI: {self.config.well_known_oidc_config_uri}")
            raise

    def _get_well_known_uri_from_url(self, provider):
        # TODO: Look up this URL from a Python library
        base_url = self.config.url
        # Remove potential trailing slash to avoid "//realms"
        base_url = base_url if base_url[-1] != "/" else base_url[:-1]
        return f"{base_url}/.well-known/openid-configuration"

    def _load_well_known_oidc_config(self, well_known_oidc_config):
        self.config.authorization_endpoint = well_known_oidc_config["authorization_endpoint"]
        self.config.token_endpoint = well_known_oidc_config["token_endpoint"]
        self.config.userinfo_endpoint = well_known_oidc_config["userinfo_endpoint"]
        self.config.end_session_endpoint = well_known_oidc_config.get("end_session_endpoint")
        self.config.issuer = well_known_oidc_config.get("issuer")
        self.config.jwks_uri = well_known_oidc_config.get("jwks_uri")
        if self.config.jwks_uri:
            self.jwks_client = jwt.PyJWKClient(self.config.jwks_uri, cache_jwk_set=True, lifespan=360)
        else:
            self.jwks_client = None

    def _get_verify_param(self):
        """Return 'ca_bundle' if 'verify_ssl' is true and 'ca_bundle' is configured."""
        # in requests_oauthlib, the verify param can either be a boolean or a CA bundle path
        if self.config.ca_bundle is not None and self.config.verify_ssl:
            return self.config.ca_bundle
        else:
            return self.config.verify_ssl

    @staticmethod
    def _username_from_userinfo(trans, userinfo):
        username = userinfo.get("preferred_username", userinfo["email"])
        if "@" in username:
            username = username.split("@")[0]  # username created from username portion of email
        username = util.ready_name_for_url(username).lower()
        if trans.sa_session.query(User).filter_by(username=username).first():
            # if username already exists in database, append integer and iterate until unique username found
            count = 0
            while trans.sa_session.query(User).filter_by(username=(f"{username}{count}")).first():
                count += 1
            return f"{username}{count}"
        else:
            return username

    def decode_user_access_token(self, sa_session, access_token):
        """Verifies and decodes an access token against this provider, returning the user and
        a dict containing the decoded token data.

        :type  sa_session:      sqlalchemy.orm.scoping.scoped_session
        :param sa_session:      SQLAlchemy database handle.

        :type  access_token: string
        :param access_token: An OIDC access token

        :return: A tuple containing the user and decoded jwt data or [None, None]
                 if the access token does not belong to this provider.
        :rtype: Tuple[User, dict]
        """
        if not self.jwks_client:
            return None
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(access_token)
            decoded_jwt = jwt.decode(
                access_token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self.config.issuer,
                audience=self.config.accepted_audiences,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": bool(self.config.accepted_audiences),
                    "verify_iss": True,
                },
            )
        except jwt.exceptions.PyJWKClientError:
            log.debug(f"Could not get signing keys for access token with provider: {self.config.provider}. Ignoring...")
            return None, None
        except jwt.exceptions.InvalidIssuerError:
            # An Invalid issuer means that the access token is not relevant to this provider.
            # All other exceptions are bubbled up
            return None, None
        # jwt verified, we can now fetch the user
        user_id = decoded_jwt["sub"]
        custos_authnz_token = self._get_custos_authnz_token(sa_session, user_id, self.config.provider)
        user = custos_authnz_token.user if custos_authnz_token else None
        return user, decoded_jwt


class OIDCAuthnzBaseKeycloak(OIDCAuthnzBase):
    def __init__(self, provider, oidc_config, oidc_backend_config, idphint=None):
        super().__init__(provider, oidc_config, oidc_backend_config, idphint)
        self.config.extra_params = {"kc_idp_hint": oidc_backend_config.get("idphint", "oidc")}
        self._load_config()


class OIDCAuthnzBaseCiLogon(OIDCAuthnzBase):
    def __init__(self, provider, oidc_config, oidc_backend_config, idphint=None):
        super().__init__(provider, oidc_config, oidc_backend_config, idphint)
        self.config.extra_params = {"kc_idp_hint": oidc_backend_config.get("idphint", "cilogon")}
        self._load_config()

    def _get_provider_specific_scopes(self):
        return ["org.cilogon.userinfo"]

    def _get_well_known_uri_from_url(self, provider):
        base_url = self.config.url
        # backwards compatibility. CILogon URL is given with /authorize in the examples. not sure if
        # this applies to the wild, but let's be safe here and remove the /authorize if it exists
        # which will lead to the correct openid configuration
        base_url = base_url if base_url.split("/")[-1] != "authorize" else "/".join(base_url.split("/")[:-1])
        return f"{base_url}/.well-known/openid-configuration"


class CustosAuthFactory:
    @dataclass
    class _CustosAuthBasedProviderCacheItem:
        created_at: datetime
        item: OIDCAuthnzBase
        provider: str
        oidc_config: dict
        oidc_backend_config: dict
        idphint: str

    _CustosAuthBasedProvidersCache: list[_CustosAuthBasedProviderCacheItem] = []

    @staticmethod
    def GetCustosBasedAuthProvider(provider, oidc_config, oidc_backend_config, idphint=None):
        # see if we have a config loaded up already
        for item in CustosAuthFactory._CustosAuthBasedProvidersCache:
            if (
                item.provider == provider
                and item.oidc_config == oidc_config
                and item.oidc_backend_config == oidc_backend_config
                and item.idphint == idphint
            ):
                return item.item

        auth_adapter: OIDCAuthnzBase
        if provider.lower() == "custos":
            auth_adapter = OIDCAuthnzBaseCustos(provider, oidc_config, oidc_backend_config, idphint)
        elif provider.lower() == "keycloak":
            auth_adapter = OIDCAuthnzBaseKeycloak(provider, oidc_config, oidc_backend_config, idphint)
        elif provider.lower() == "cilogon":
            auth_adapter = OIDCAuthnzBaseCiLogon(provider, oidc_config, oidc_backend_config, idphint)
        else:
            raise Exception(f"Unknown Custos provider name: {provider}")

        if auth_adapter:
            CustosAuthFactory._CustosAuthBasedProvidersCache.append(
                CustosAuthFactory._CustosAuthBasedProviderCacheItem(
                    created_at=datetime.now(),
                    item=auth_adapter,
                    provider=provider,
                    oidc_config=oidc_config,
                    oidc_backend_config=oidc_backend_config,
                    idphint=idphint,
                )
            )

        return auth_adapter


class OIDCAuthnzBaseCustos(OIDCAuthnzBase):
    def __init__(self, provider, oidc_config, oidc_backend_config, idphint=None):
        super().__init__(provider, oidc_config, oidc_backend_config, idphint)
        self.config.extra_params = {"kc_idp_hint": oidc_backend_config.get("idphint", "oidc")}
        self._load_config_for_custos()

    def _get_custos_credentials(self):
        clientIdAndSec = f"{self.config.client_id}:{self.config.client_secret}"
        if not self.config.credential_url:
            raise Exception(
                f"Error OIDC provider {self.config.provider} is of type Custos, but does not have the credential url set"
            )
        creds = requests.get(
            self.config.credential_url,
            headers={"Authorization": f"Basic {util.unicodify(base64.b64encode(util.smart_str(clientIdAndSec)))}"},
            verify=False,
            params={"client_id": self.config.client_id},
            timeout=util.DEFAULT_SOCKET_TIMEOUT,
        )
        credentials = creds.json()
        self.config.iam_client_secret = credentials["iam_client_secret"]

    def _load_config_for_custos(self):
        self.config.credential_url = f"{self.config.url.rstrip('/')}/credentials"
        self._get_custos_credentials()
        # Set custos endpoints
        clientIdAndSec = f"{self.config.client_id}:{self.config.client_secret}"
        headers = {"Authorization": f"Basic {util.unicodify(base64.b64encode(util.smart_str(clientIdAndSec)))}"}
        params = {"client_id": self.config.client_id}

        self._load_config(headers, params)
