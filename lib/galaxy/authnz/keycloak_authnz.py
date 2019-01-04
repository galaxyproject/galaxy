
import hashlib
import json
import logging
from datetime import datetime, timedelta

import jwt
from oauthlib.common import generate_nonce
from requests_oauthlib import OAuth2Session

from galaxy.model import KeycloakAccessToken, User
from ..authnz import IdentityProvider

log = logging.getLogger(__name__)


class KeycloakAuthnz(IdentityProvider):
    def __init__(self, provider, oidc_config, oidc_backend_config):
        self.config = {'provider': provider.lower()}
        self.config['verify_ssl'] = oidc_config['VERIFY_SSL']
        self.config['client_id'] = oidc_backend_config['client_id']
        self.config['client_secret'] = oidc_backend_config['client_secret']
        self.config['redirect_uri'] = oidc_backend_config['redirect_uri']
        self.config['authorization_endpoint'] = oidc_backend_config['authorization_endpoint']
        self.config['token_endpoint'] = oidc_backend_config['token_endpoint']
        self.config['userinfo_endpoint'] = oidc_backend_config['userinfo_endpoint']
        self.config['idp_hint'] = oidc_backend_config.get('idp_hint', None)

    def authenticate(self, trans):
        client_id = self.config['client_id']
        base_authorize_url = self.config['authorization_endpoint']
        redirect_uri = self.config['redirect_uri']
        oauth2_session = OAuth2Session(
            client_id, scope=('openid', 'email', 'profile'), redirect_uri=redirect_uri)
        nonce = generate_nonce()
        nonce_hash = hashlib.sha256(nonce).hexdigest()
        extra_params = {"nonce": nonce_hash}
        if self.config['idp_hint']:
            extra_params['kc_idp_hint'] = self.config['idp_hint']
        authorization_url, state = oauth2_session.authorization_url(
            base_authorize_url, **extra_params)
        trans.set_cookie(value=state, name='keycloakauth-state')
        trans.set_cookie(value=nonce, name='keycloakauth-nonce')
        return authorization_url

    def callback(self, state_token, authz_code, trans, login_redirect_url):
        client_id = self.config['client_id']
        client_secret = self.config['client_secret']
        redirect_uri = self.config['redirect_uri']
        token_endpoint = self.config['token_endpoint']
        userinfo_endpoint = self.config['userinfo_endpoint']
        # Take state value to validate from token. OAuth2Session.fetch_token
        # will validate that the state query parameter value on the URL matches
        # this value.
        state_cookie = trans.get_cookie(name='keycloakauth-state')
        oauth2_session = OAuth2Session(client_id,
                                       scope=('openid', 'email', 'profile'),
                                       redirect_uri=redirect_uri,
                                       state=state_cookie)
        token = oauth2_session.fetch_token(
            token_endpoint, client_secret=client_secret,
            authorization_response=trans.request.url)
        log.debug("token={}".format(json.dumps(token, indent=True)))
        access_token = token['access_token']
        id_token = token['id_token']
        refresh_token = token['refresh_token']
        expiration_time = datetime.now() + timedelta(seconds=token['expires_in'])
        refresh_expiration_time = datetime.now() + timedelta(seconds=token['refresh_expires_in'])
        # get nonce from token['id_token'] and validate
        id_token_decoded = jwt.decode(id_token, verify=False)
        nonce_hash = id_token_decoded['nonce']
        nonce_cookie = trans.get_cookie(name='keycloakauth-nonce')
        # Delete the nonce cookie
        trans.set_cookie('', name='keycloakauth-nonce', age=-1)
        nonce_cookie_hash = hashlib.sha256(nonce_cookie).hexdigest()
        if nonce_hash != nonce_cookie_hash:
            raise Exception("Nonce mismatch!")
        userinfo = oauth2_session.get(userinfo_endpoint).json()
        log.debug("userinfo={}".format(json.dumps(userinfo, indent=True)))
        username = userinfo["preferred_username"]
        email = userinfo["email"]
        user = self._get_user(trans.sa_session, username, email)
        keycloak_access_token = KeycloakAccessToken(user=user,
                                                    access_token=access_token,
                                                    id_token=id_token,
                                                    refresh_token=refresh_token,
                                                    expiration_time=expiration_time,
                                                    refresh_expiration_time=refresh_expiration_time,
                                                    raw_token=token)
        trans.sa_session.add(keycloak_access_token)
        trans.sa_session.flush()
        return login_redirect_url, user

    def disconnect(self, provider, trans, disconnect_redirect_url=None, association_id=None):
        # TODO: implement
        pass

    def _get_user(self, sa_session, username, email):
        user = sa_session.query(User).filter_by(username=username).first()
        if not user:
            user = self._create_user(sa_session, username, email)
        return user

    def _create_user(self, sa_session, username, email):
        user = User(email=email, username=username)
        user.set_random_password()
        sa_session.add(user)
        sa_session.flush()
        return user
