
import hashlib
import unittest

import jwt
import requests
from six.moves.urllib.parse import parse_qs, urlparse

from galaxy.authnz import keycloak_authnz
from galaxy.model import User


class KeycloakAuthnzTestCase(unittest.TestCase):

    _create_oauth2_session_called = False
    _fetch_token_called = False
    _get_userinfo_called = False

    def setUp(self):
        self.orig_requests_get = requests.get
        requests.get = self.mockRequest("https://test-well-known-oidc-config-uri", {
            "authorization_endpoint": "https://test-auth-endpoint",
            "token_endpoint": "https://test-token-endpoint",
            "userinfo_endpoint": "https://test-userinfo-endpoint"
        })
        self.keycloak_authnz = keycloak_authnz.KeycloakAuthnz('Google', {
            'VERIFY_SSL': True
        }, {
            'client_id': 'test-client-id',
            'client_secret': 'test-client-secret',
            'redirect_uri': 'https://test-redirect-uri',
            'well_known_oidc_config_uri': 'https://test-well-known-oidc-config-uri'
        })
        # self.mock_create_oauth2_session(self.keycloak_authnz)
        self.mock_fetch_token(self.keycloak_authnz)
        self.mock_get_userinfo(self.keycloak_authnz)
        self.trans = self.mockTrans()
        self.test_state = "abc123"
        self.test_nonce = "4662892146306485421546981092"
        self.test_nonce_hash = hashlib.sha256(self.test_nonce).hexdigest()
        self.test_code = "test-code"
        self.trans.request.url = "https://localhost:8000/authnz/galaxy-auth/keycloak/callback?state={test_state}&code={test_code}".format(test_state=self.test_state, test_code=self.test_code)

    def mock_create_oauth2_session(self, keycloak_authnz):
        orig_create_oauth2_session = keycloak_authnz._create_oauth2_session

        def create_oauth2_session(state=None):
            self._create_oauth2_session_called = True
            assert state == self.test_state
            return orig_create_oauth2_session(state)
        keycloak_authnz._create_oauth2_session = create_oauth2_session

    def mock_fetch_token(self, keycloak_authnz):
        def fetch_token(oauth2_session, trans):
            self._fetch_token_called = True
            return {
                "access_token": "test_access_token",
                "id_token": jwt.encode({'nonce': self.test_nonce_hash}, key=None, algorithm=None),
                "refresh_token": "test_refresh_token",
                "expires_in": 30,
                "refresh_expires_in": 1800
            }
        keycloak_authnz._fetch_token = fetch_token

    def mock_get_userinfo(self, keycloak_authnz):
        def get_userinfo(oauth2_session):
            self._get_userinfo_called = True
            return {
                "preferred_username": "test-username",
                "email": "test-email"
            }
        keycloak_authnz._get_userinfo = get_userinfo

    def mockRequest(self, url, resp):
        def get(x):
            assert x == url
            return Response()

        class Response(object):
            def json(self):
                return resp

        return get

    def mockTrans(self):

        class Request:
            url = None

        class QueryResult:
            results = []

            def first(self):
                if len(self.results) > 0:
                    return self.results[0]
                else:
                    return None

        class Query:
            username = None
            user = None

            def filter_by(self, username=None):
                self.username = username
                result = QueryResult()
                if self.user:
                    result.results.append(self.user)
                return result

        class Session:
            items = []
            flush_called = False
            _query = Query()

            def add(self, item):
                self.items.append(item)

            def flush(self):
                self.flush_called = True

            def query(self, cls):
                return self._query

        class Trans:
            cookies = {}
            cookies_args = {}
            request = Request()
            sa_session = Session()

            def set_cookie(self, value, name=None, **kwargs):
                self.cookies[name] = value
                self.cookies_args[name] = kwargs

            def get_cookie(self, name):
                return self.cookies[name]

        return Trans()

    def tearDown(self):
        requests.get = self.orig_requests_get

    def test_parse_config(self):
        self.assertTrue(self.keycloak_authnz.config['verify_ssl'])
        self.assertEqual(self.keycloak_authnz.config['client_id'], 'test-client-id')
        self.assertEqual(self.keycloak_authnz.config['client_secret'], 'test-client-secret')
        self.assertEqual(self.keycloak_authnz.config['redirect_uri'], 'https://test-redirect-uri')
        self.assertEqual(self.keycloak_authnz.config['well_known_oidc_config_uri'], 'https://test-well-known-oidc-config-uri')
        self.assertEqual(self.keycloak_authnz.config['authorization_endpoint'], 'https://test-auth-endpoint')
        self.assertEqual(self.keycloak_authnz.config['token_endpoint'], 'https://test-token-endpoint')
        self.assertEqual(self.keycloak_authnz.config['userinfo_endpoint'], 'https://test-userinfo-endpoint')

    def test_authenticate_set_state_cookie(self):
        """Verify that authenticate() sets a state cookie."""
        authorization_url = self.keycloak_authnz.authenticate(self.trans)
        parsed = urlparse(authorization_url)
        state = parse_qs(parsed.query)['state'][0]
        self.assertEqual(state, self.trans.cookies[keycloak_authnz.STATE_COOKIE_NAME])

    def test_authenticate_set_nonce_cookie(self):
        """Verify that authenticate() sets a nonce cookie."""
        authorization_url = self.keycloak_authnz.authenticate(self.trans)
        parsed = urlparse(authorization_url)
        hashed_nonce_in_url = parse_qs(parsed.query)['nonce'][0]
        nonce_in_cookie = self.trans.cookies[keycloak_authnz.NONCE_COOKIE_NAME]
        hashed_nonce = self.keycloak_authnz._hash_nonce(nonce_in_cookie)
        self.assertEqual(hashed_nonce, hashed_nonce_in_url)

    def test_callback_verify_with_state_cookie(self):
        """Verify that state from cookie is passed to OAuth2Session constructor."""
        self.trans.set_cookie(value=self.test_state, name=keycloak_authnz.STATE_COOKIE_NAME)
        self.trans.set_cookie(value=self.test_nonce, name=keycloak_authnz.NONCE_COOKIE_NAME)
        self.trans.sa_session._query.user = User(email="test@example.com", username="test-user")

        # Mock _create_oauth2_session to make sure it is created with cookie state token
        self.mock_create_oauth2_session(self.keycloak_authnz)

        # Intentionally passing a bad state_token to make sure that code under
        # test uses the state cookie instead when creating the OAuth2Session
        self.keycloak_authnz.callback(state_token="xxx",
                                      authz_code=self.test_code, trans=self.trans,
                                      login_redirect_url="http://localhost:8000/")
        self.assertTrue(self._create_oauth2_session_called)
        self.assertTrue(self._fetch_token_called)
        self.assertTrue(self._get_userinfo_called)

    def test_callback_nonce_validation_with_bad_nonce(self):
        self.trans.set_cookie(value=self.test_state, name=keycloak_authnz.STATE_COOKIE_NAME)
        self.trans.set_cookie(value=self.test_nonce, name=keycloak_authnz.NONCE_COOKIE_NAME)
        self.trans.sa_session._query.user = User(email="test@example.com", username="test-user")

        # Intentionally create a bad nonce
        self.test_nonce_hash = self.test_nonce_hash + "Z"

        # self.keycloak_authnz._fetch_token = fetch_token
        with self.assertRaises(Exception):
            self.keycloak_authnz.callback(state_token="xxx",
                                        authz_code=self.test_code, trans=self.trans,
                                        login_redirect_url="http://localhost:8000/")
        self.assertTrue(self._fetch_token_called)
        self.assertFalse(self._get_userinfo_called)
