
from requests_oauthlib import OAuth2Session

from ..authnz import IdentityProvider


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

    def authenticate(self, trans):
        client_id = self.config['client_id']
        base_authorize_url = self.config['authorization_endpoint']
        redirect_uri = self.config['redirect_uri']
        oauth2_session = OAuth2Session(
            client_id, scope=('openid', 'email', 'profile'), redirect_uri=redirect_uri)
        # TODO: Add nonce to authorization_url?
        authorization_url, state = oauth2_session.authorization_url(
            base_authorize_url)
        # TODO: store state and redirect_uri in database
        return authorization_url

    def callback(self, state_token, authz_code, trans, login_redirect_url):
        pass

    def disconnect(self, provider, trans, disconnect_redirect_url=None, association_id=None):
        pass
