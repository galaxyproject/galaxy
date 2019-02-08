
import hashlib
import unittest
import uuid
from datetime import datetime, timedelta

import jwt
import requests
from six.moves.urllib.parse import parse_qs, urlparse

from galaxy.authnz import oidc_authnz
from galaxy.model import KeycloakAccessToken, User


class OIDCAuthnzTestCase(unittest.TestCase):

    _create_oauth2_session_called = False
    _fetch_token_called = False
    _get_userinfo_called = False
    _raw_token = None

    def setUp(self):
        self.orig_requests_get = requests.get
        requests.get = self.mockRequest("https://test-well-known-oidc-config-uri", {
            "authorization_endpoint": "https://test-auth-endpoint",
            "token_endpoint": "https://test-token-endpoint",
            "userinfo_endpoint": "https://test-userinfo-endpoint"
        })
        self.oidc_authnz = oidc_authnz.OIDCAuthnz('Google', {
            'VERIFY_SSL': True
        }, {
            'client_id': 'test-client-id',
            'client_secret': 'test-client-secret',
            'redirect_uri': 'https://test-redirect-uri',
            'well_known_oidc_config_uri': 'https://test-well-known-oidc-config-uri'
        })
        self.mock_fetch_token(self.oidc_authnz)
        self.mock_get_userinfo(self.oidc_authnz)
        self.trans = self.mockTrans()
        self.test_state = "abc123"
        self.test_nonce = "4662892146306485421546981092"
        self.test_nonce_hash = hashlib.sha256(self.test_nonce).hexdigest()
        self.test_code = "test-code"
        self.test_username = "test-username"
        self.test_email = "test-email"
        self.test_access_token = "test_access_token"
        self.test_refresh_token = "test_refresh_token"
        self.test_expires_in = 30
        self.test_refresh_expires_in = 1800
        self.test_keycloak_user_id = str(uuid.uuid4())
        self.trans.request.url = "https://localhost:8000/authnz/galaxy-auth/keycloak/callback?state={test_state}&code={test_code}".format(test_state=self.test_state, test_code=self.test_code)

    @property
    def test_id_token(self):
        return jwt.encode({'nonce': self.test_nonce_hash}, key=None, algorithm=None)

    def mock_create_oauth2_session(self, oidc_authnz):
        orig_create_oauth2_session = oidc_authnz._create_oauth2_session

        def create_oauth2_session(state=None):
            self._create_oauth2_session_called = True
            assert state == self.test_state
            return orig_create_oauth2_session(state)
        oidc_authnz._create_oauth2_session = create_oauth2_session

    def mock_fetch_token(self, oidc_authnz):
        def fetch_token(oauth2_session, trans):
            self._fetch_token_called = True
            self._raw_token = {
                "access_token": self.test_access_token,
                "id_token": self.test_id_token,
                "refresh_token": self.test_refresh_token,
                "expires_in": self.test_expires_in,
                "refresh_expires_in": self.test_refresh_expires_in
            }
            return self._raw_token
        oidc_authnz._fetch_token = fetch_token

    def mock_get_userinfo(self, oidc_authnz):
        def get_userinfo(oauth2_session):
            self._get_userinfo_called = True
            return {
                "preferred_username": self.test_username,
                "email": self.test_email,
                "sub": self.test_keycloak_user_id
            }
        oidc_authnz._get_userinfo = get_userinfo

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

            def __init__(self, results=None):
                if results:
                    self.results = results

            def first(self):
                if len(self.results) > 0:
                    return self.results[0]
                else:
                    return None

            def one_or_none(self):
                if len(self.results) == 1:
                    return self.results[0]
                elif len(self.results) == 0:
                    return None
                else:
                    raise Exception("More than one result!")

        class Query:
            keycloak_user_id = None
            keycloak_access_token = None

            def filter_by(self, keycloak_user_id=None):
                self.keycloak_user_id = keycloak_user_id
                if self.keycloak_access_token:
                    return QueryResult([self.keycloak_access_token])
                else:
                    return QueryResult()

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
        self.assertTrue(self.oidc_authnz.config['verify_ssl'])
        self.assertEqual(self.oidc_authnz.config['client_id'], 'test-client-id')
        self.assertEqual(self.oidc_authnz.config['client_secret'], 'test-client-secret')
        self.assertEqual(self.oidc_authnz.config['redirect_uri'], 'https://test-redirect-uri')
        self.assertEqual(self.oidc_authnz.config['well_known_oidc_config_uri'], 'https://test-well-known-oidc-config-uri')
        self.assertEqual(self.oidc_authnz.config['authorization_endpoint'], 'https://test-auth-endpoint')
        self.assertEqual(self.oidc_authnz.config['token_endpoint'], 'https://test-token-endpoint')
        self.assertEqual(self.oidc_authnz.config['userinfo_endpoint'], 'https://test-userinfo-endpoint')

    def test_authenticate_set_state_cookie(self):
        """Verify that authenticate() sets a state cookie."""
        authorization_url = self.oidc_authnz.authenticate(self.trans)
        parsed = urlparse(authorization_url)
        state = parse_qs(parsed.query)['state'][0]
        self.assertEqual(state, self.trans.cookies[oidc_authnz.STATE_COOKIE_NAME])

    def test_authenticate_set_nonce_cookie(self):
        """Verify that authenticate() sets a nonce cookie."""
        authorization_url = self.oidc_authnz.authenticate(self.trans)
        parsed = urlparse(authorization_url)
        hashed_nonce_in_url = parse_qs(parsed.query)['nonce'][0]
        nonce_in_cookie = self.trans.cookies[oidc_authnz.NONCE_COOKIE_NAME]
        hashed_nonce = self.oidc_authnz._hash_nonce(nonce_in_cookie)
        self.assertEqual(hashed_nonce, hashed_nonce_in_url)

    def test_callback_verify_with_state_cookie(self):
        """Verify that state from cookie is passed to OAuth2Session constructor."""
        self.trans.set_cookie(value=self.test_state, name=oidc_authnz.STATE_COOKIE_NAME)
        self.trans.set_cookie(value=self.test_nonce, name=oidc_authnz.NONCE_COOKIE_NAME)
        self.trans.sa_session._query.user = User(email=self.test_email, username=self.test_username)

        # Mock _create_oauth2_session to make sure it is created with cookie state token
        self.mock_create_oauth2_session(self.oidc_authnz)

        # Intentionally passing a bad state_token to make sure that code under
        # test uses the state cookie instead when creating the OAuth2Session
        login_redirect_url, user = self.oidc_authnz.callback(
            state_token="xxx",
            authz_code=self.test_code, trans=self.trans,
            login_redirect_url="http://localhost:8000/")
        self.assertTrue(self._create_oauth2_session_called)
        self.assertTrue(self._fetch_token_called)
        self.assertTrue(self._get_userinfo_called)
        self.assertEqual(login_redirect_url, "http://localhost:8000/")
        self.assertIsNotNone(user)

    def test_callback_nonce_validation_with_bad_nonce(self):
        self.trans.set_cookie(value=self.test_state, name=oidc_authnz.STATE_COOKIE_NAME)
        self.trans.set_cookie(value=self.test_nonce, name=oidc_authnz.NONCE_COOKIE_NAME)
        self.trans.sa_session._query.user = User(email=self.test_email, username=self.test_username)

        # Intentionally create a bad nonce
        self.test_nonce_hash = self.test_nonce_hash + "Z"

        # self.oidc_authnz._fetch_token = fetch_token
        with self.assertRaises(Exception):
            self.oidc_authnz.callback(state_token="xxx",
                                      authz_code=self.test_code, trans=self.trans,
                                      login_redirect_url="http://localhost:8000/")
        self.assertTrue(self._fetch_token_called)
        self.assertFalse(self._get_userinfo_called)

    def test_callback_galaxy_user_created_when_no_access_token_exists(self):
        self.trans.set_cookie(value=self.test_state, name=oidc_authnz.STATE_COOKIE_NAME)
        self.trans.set_cookie(value=self.test_nonce, name=oidc_authnz.NONCE_COOKIE_NAME)

        self.assertIsNone(self.trans.sa_session.query(KeycloakAccessToken).filter_by(keycloak_user_id=self.test_keycloak_user_id).one_or_none())
        self.assertEqual(0, len(self.trans.sa_session.items))
        login_redirect_url, user = self.oidc_authnz.callback(
            state_token="xxx",
            authz_code=self.test_code, trans=self.trans,
            login_redirect_url="http://localhost:8000/")
        self.assertTrue(self._fetch_token_called)
        self.assertTrue(self._get_userinfo_called)
        self.assertEqual(2, len(self.trans.sa_session.items), "Session has new User and new KeycloakAccessToken")
        added_user = self.trans.sa_session.items[0]
        self.assertIsInstance(added_user, User)
        self.assertEqual(self.test_username, added_user.username)
        self.assertEqual(self.test_email, added_user.email)
        self.assertIsNotNone(added_user.password)
        # Verify keycloak_access_token_record
        added_keycloak_access_token = self.trans.sa_session.items[1]
        self.assertIsInstance(added_keycloak_access_token, KeycloakAccessToken)
        self.assertIs(user, added_keycloak_access_token.user)
        self.assertEqual(self.test_access_token, added_keycloak_access_token.access_token)
        self.assertEqual(self.test_id_token, added_keycloak_access_token.id_token)
        self.assertEqual(self.test_refresh_token, added_keycloak_access_token.refresh_token)
        expected_expiration_time = datetime.now() + timedelta(seconds=self.test_expires_in)
        expiration_timedelta = expected_expiration_time - added_keycloak_access_token.expiration_time
        self.assertTrue(expiration_timedelta.total_seconds() < 1)
        expected_refresh_expiration_time = datetime.now() + timedelta(seconds=self.test_refresh_expires_in)
        refresh_expiration_timedelta = expected_refresh_expiration_time - added_keycloak_access_token.refresh_expiration_time
        self.assertTrue(refresh_expiration_timedelta.total_seconds() < 1)
        self.assertEqual(self._raw_token, added_keycloak_access_token.raw_token)
        self.assertTrue(self.trans.sa_session.flush_called)

    def test_callback_galaxy_user_not_created_when_keycloak_access_token_exists(self):
        self.trans.set_cookie(value=self.test_state, name=oidc_authnz.STATE_COOKIE_NAME)
        self.trans.set_cookie(value=self.test_nonce, name=oidc_authnz.NONCE_COOKIE_NAME)
        old_access_token = "old-access-token"
        old_id_token = "old-id-token"
        old_refresh_token = "old-refresh-token"
        old_expiration_time = datetime.now() - timedelta(days=1)
        old_refresh_expiration_time = datetime.now() - timedelta(hours=3)
        old_raw_token = "{}"
        existing_keycloak_access_token = KeycloakAccessToken(
            user=User(email=self.test_email, username=self.test_username),
            keycloak_user_id=self.test_keycloak_user_id,
            access_token=old_access_token,
            id_token=old_id_token,
            refresh_token=old_refresh_token,
            expiration_time=old_expiration_time,
            refresh_expiration_time=old_refresh_expiration_time,
            raw_token=old_raw_token,
        )

        self.trans.sa_session._query.keycloak_access_token = existing_keycloak_access_token

        self.assertIsNotNone(self.trans.sa_session.query(KeycloakAccessToken).filter_by(keycloak_user_id=self.test_keycloak_user_id).one_or_none())
        self.assertEqual(0, len(self.trans.sa_session.items))
        login_redirect_url, user = self.oidc_authnz.callback(
            state_token="xxx",
            authz_code=self.test_code, trans=self.trans,
            login_redirect_url="http://localhost:8000/")
        self.assertTrue(self._fetch_token_called)
        self.assertTrue(self._get_userinfo_called)
        self.assertEqual(1, len(self.trans.sa_session.items), "Session has updated KeycloakAccessToken")
        session_keycloak_access_token = self.trans.sa_session.items[0]
        self.assertIsInstance(session_keycloak_access_token, KeycloakAccessToken)
        self.assertIs(existing_keycloak_access_token, session_keycloak_access_token, "existing KeycloakAccessToken should be updated")
        # Verify both that existing keycloak_access_token has the correct values and different values than before
        self.assertEqual(self.test_access_token, session_keycloak_access_token.access_token)
        self.assertNotEqual(old_access_token, session_keycloak_access_token.access_token)
        self.assertEqual(self.test_id_token, session_keycloak_access_token.id_token)
        self.assertNotEqual(old_id_token, session_keycloak_access_token.id_token)
        self.assertEqual(self.test_refresh_token, session_keycloak_access_token.refresh_token)
        self.assertNotEqual(old_refresh_token, session_keycloak_access_token.refresh_token)
        expected_expiration_time = datetime.now() + timedelta(seconds=self.test_expires_in)
        expiration_timedelta = expected_expiration_time - session_keycloak_access_token.expiration_time
        self.assertTrue(expiration_timedelta.total_seconds() < 1)
        self.assertNotEqual(old_expiration_time, session_keycloak_access_token.expiration_time)
        expected_refresh_expiration_time = datetime.now() + timedelta(seconds=self.test_refresh_expires_in)
        refresh_expiration_timedelta = expected_refresh_expiration_time - session_keycloak_access_token.refresh_expiration_time
        self.assertTrue(refresh_expiration_timedelta.total_seconds() < 1)
        self.assertNotEqual(old_refresh_expiration_time, session_keycloak_access_token.refresh_expiration_time)
        self.assertEqual(self._raw_token, session_keycloak_access_token.raw_token)
        self.assertNotEqual(old_raw_token, session_keycloak_access_token.raw_token)
        self.assertTrue(self.trans.sa_session.flush_called)
