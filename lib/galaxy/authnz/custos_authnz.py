
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta

import jwt
import requests
from oauthlib.common import generate_nonce
from requests_oauthlib import OAuth2Session

from galaxy import util
from galaxy.model import CustosAuthnzToken, User
from ..authnz import IdentityProvider

log = logging.getLogger(__name__)
STATE_COOKIE_NAME = 'custos-state'
NONCE_COOKIE_NAME = 'custos-nonce'


class CustosAuthnz(IdentityProvider):
    def __init__(self, provider, oidc_config, oidc_backend_config):
        self.config = {'provider': provider.lower()}
        self.config['verify_ssl'] = oidc_config['VERIFY_SSL']
        self.config['url'] = oidc_backend_config['url']
        self.config['client_id'] = oidc_backend_config['client_id']
        self.config['client_secret'] = oidc_backend_config['client_secret']
        self.config['redirect_uri'] = oidc_backend_config['redirect_uri']
        self.config['ca_bundle'] = oidc_backend_config.get('ca_bundle', None)
        self.config['extra_params'] = {
            'kc_idp_hint': oidc_backend_config.get('idphint', 'cilogon')
        }
        # Either get OIDC config from well-known config URI or lookup known urls based on provider name and realm
        if 'well_known_oidc_config_uri' in oidc_backend_config:
            self.config['well_known_oidc_config_uri'] = oidc_backend_config['well_known_oidc_config_uri']
            well_known_oidc_config = self._load_well_known_oidc_config(
                self.config['well_known_oidc_config_uri'])
            self.config['authorization_endpoint'] = well_known_oidc_config['authorization_endpoint']
            self.config['token_endpoint'] = well_known_oidc_config['token_endpoint']
            self.config['userinfo_endpoint'] = well_known_oidc_config['userinfo_endpoint']
        else:
            realm = oidc_backend_config['realm']
            self._load_config_for_provider_and_realm(self.config['provider'], realm)

    def authenticate(self, trans):
        base_authorize_url = self.config['authorization_endpoint']
        oauth2_session = self._create_oauth2_session(scope=('openid', 'email', 'profile'))
        nonce = generate_nonce()
        nonce_hash = self._hash_nonce(nonce)
        extra_params = {"nonce": nonce_hash}
        if "extra_params" in self.config:
            extra_params.update(self.config['extra_params'])
        authorization_url, state = oauth2_session.authorization_url(
            base_authorize_url, **extra_params)
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
        log.debug("token={}".format(json.dumps(token, indent=True)))
        access_token = token['access_token']
        id_token = token['id_token']
        refresh_token = token['refresh_token'] if 'refresh_token' in token else None
        expiration_time = datetime.now() + timedelta(seconds=token['expires_in'])
        refresh_expiration_time = (datetime.now() + timedelta(seconds=token['refresh_expires_in'])) if 'refresh_expires_in' in token else None

        # Get nonce from token['id_token'] and validate. 'nonce' in the
        # id_token is a hash of the nonce stored in the NONCE_COOKIE_NAME
        # cookie.
        id_token_decoded = jwt.decode(id_token, verify=False)
        nonce_hash = id_token_decoded['nonce']
        self._validate_nonce(trans, nonce_hash)

        # Get userinfo and lookup/create Galaxy user record
        userinfo = self._get_userinfo(oauth2_session)
        log.debug("userinfo={}".format(json.dumps(userinfo, indent=True)))
        username = userinfo['preferred_username']
        email = userinfo['email']
        user_id = userinfo['sub']

        # Create or update custos_authnz_token record
        custos_authnz_token = self._get_custos_authnz_token(trans.sa_session, user_id, self.config['provider'])
        if custos_authnz_token is None:
            user = self._get_current_user(trans)
            if not user:
                user = self._create_user(trans.sa_session, username, email)
            custos_authnz_token = CustosAuthnzToken(user=user,
                                   external_user_id=user_id,
                                   provider=self.config['provider'],
                                   access_token=access_token,
                                   id_token=id_token,
                                   refresh_token=refresh_token,
                                   expiration_time=expiration_time,
                                   refresh_expiration_time=refresh_expiration_time)
        else:
            custos_authnz_token.access_token = access_token
            custos_authnz_token.id_token = id_token
            custos_authnz_token.refresh_token = refresh_token
            custos_authnz_token.expiration_time = expiration_time
            custos_authnz_token.refresh_expiration_time = refresh_expiration_time
        trans.sa_session.add(custos_authnz_token)
        trans.sa_session.flush()
        return login_redirect_url, custos_authnz_token.user

    def disconnect(self, provider, trans, disconnect_redirect_url=None):
        try:
            user = trans.user
            # Find CustosAuthnzToken record for this provider (should only be one)
            provider_tokens = [token for token in user.custos_auth if token.provider == self.config["provider"]]
            if len(provider_tokens) == 0:
                raise Exception("User is not associated with provider {}".format(self.config["provider"]))
            if len(provider_tokens) > 1:
                raise Exception("User is associated more than once with provider {}".format(self.config["provider"]))
            trans.sa_session.delete(provider_tokens[0])
            trans.sa_session.flush()
            return True, "", disconnect_redirect_url
        except Exception as e:
            return False, "Failed to disconnect provider {}: {}".format(provider, str(e)), None

    def _create_oauth2_session(self, state=None, scope=None):
        client_id = self.config['client_id']
        redirect_uri = self.config['redirect_uri']
        if (redirect_uri.startswith('http://localhost')
                and os.environ.get("OAUTHLIB_INSECURE_TRANSPORT", None) != "1"):
            log.warn("Setting OAUTHLIB_INSECURE_TRANSPORT to '1' to "
                     "allow plain HTTP (non-SSL) callback")
            os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = "1"
        session = OAuth2Session(client_id,
                             scope=scope,
                             redirect_uri=redirect_uri,
                             state=state)
        session.verify = self._get_verify_param()
        return session

    def _fetch_token(self, oauth2_session, trans):
        client_secret = self.config['client_secret']
        token_endpoint = self.config['token_endpoint']
        return oauth2_session.fetch_token(
            token_endpoint,
            client_secret=client_secret,
            authorization_response=trans.request.url,
            verify=self._get_verify_param())

    def _get_userinfo(self, oauth2_session):
        userinfo_endpoint = self.config['userinfo_endpoint']
        return oauth2_session.get(userinfo_endpoint,
                                  verify=self._get_verify_param()).json()

    def _get_custos_authnz_token(self, sa_session, user_id, provider):
        return sa_session.query(CustosAuthnzToken).filter_by(
            external_user_id=user_id, provider=provider).one_or_none()

    def _get_current_user(self, trans):
        return trans.user if trans.user else None

    def _create_user(self, sa_session, username, email):
        user = User(email=email, username=username)
        user.set_random_password()
        sa_session.add(user)
        sa_session.flush()
        return user

    def _hash_nonce(self, nonce):
        return hashlib.sha256(util.smart_str(nonce)).hexdigest()

    def _validate_nonce(self, trans, nonce_hash):
        nonce_cookie = trans.get_cookie(name=NONCE_COOKIE_NAME)
        # Delete the nonce cookie
        trans.set_cookie('', name=NONCE_COOKIE_NAME, age=-1)
        nonce_cookie_hash = self._hash_nonce(nonce_cookie)
        if nonce_hash != nonce_cookie_hash:
            raise Exception("Nonce mismatch!")

    def _load_config_for_provider_and_realm(self, provider, realm):
        self.config['well_known_oidc_config_uri'] = self._get_well_known_uri_for_provider_and_realm(provider, realm)
        well_known_oidc_config = self._load_well_known_oidc_config(self.config['well_known_oidc_config_uri'])
        self.config['authorization_endpoint'] = well_known_oidc_config['authorization_endpoint']
        self.config['token_endpoint'] = well_known_oidc_config['token_endpoint']
        self.config['userinfo_endpoint'] = well_known_oidc_config['userinfo_endpoint']

    def _get_well_known_uri_for_provider_and_realm(self, provider, realm):
        # TODO: Look up this URL from a Python library
        if provider == 'custos':
            return "{}/realms/{}/.well-known/openid-configuration".format(self.config["url"], realm)
        else:
            raise Exception("Unknown Custos provider name: {}".format(provider))

    def _load_well_known_oidc_config(self, well_known_uri):
        try:
            return requests.get(well_known_uri,
                                verify=self._get_verify_param()).json()
        except Exception:
            log.error("Failed to load well-known OIDC config URI: {}".format(well_known_uri))
            raise

    def _get_verify_param(self):
        """Return 'ca_bundle' if 'verify_ssl' is true and 'ca_bundle' is configured."""
        # in requests_oauthlib, the verify param can either be a boolean or a CA bundle path
        if self.config['ca_bundle'] is not None and self.config['verify_ssl']:
            return self.config['ca_bundle']
        else:
            return self.config['verify_ssl']
