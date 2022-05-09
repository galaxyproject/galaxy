import hashlib
import json
import os
import unittest
import uuid
from datetime import (
    datetime,
    timedelta,
)
from unittest import SkipTest
from urllib.parse import (
    parse_qs,
    quote,
    urlparse,
)

import jwt
import requests

from galaxy.app_unittest_utils.galaxy_mock import MockTrans
from galaxy.authnz import custos_authnz
from galaxy.model import (
    CustosAuthnzToken,
    User,
)
from galaxy.util import unicodify


class CustosAuthnzTestCase(unittest.TestCase):

    _create_oauth2_session_called = False
    _fetch_token_called = False
    _get_userinfo_called = False
    _raw_token = None

    def _get_idp_url(self):
        # it would be ideal is we can use a URI as the following:
        # https://test_base_uri/auth
        return "https://iam.scigap.org/auth"

    def _get_credential_url(self):
        return f"{self._get_idp_url()}/credentials"

    def _get_well_known_url(self):
        return f"{self._get_idp_url()}/.well-known/openid-configuration"

    def setUp(self):
        self.orig_requests_get = requests.get
        requests.get = self.mockRequest(
            {
                self._get_well_known_url(): {
                    "authorization_endpoint": "https://test-auth-endpoint",
                    "token_endpoint": "https://test-token-endpoint",
                    "userinfo_endpoint": "https://test-userinfo-endpoint",
                    "end_session_endpoint": "https://test-end-session-endpoint",
                },
                self._get_credential_url(): {"iam_client_secret": "TESTSECRET"},
            }
        )
        self.custos_authnz = custos_authnz.CustosAuthnz(
            "Custos",
            {"VERIFY_SSL": True},
            {
                "url": self._get_idp_url(),
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
                "redirect_uri": "https://test-redirect-uri",
                "realm": "test-realm",
            },
        )
        self.setupMocks()
        self.test_state = "abc123"
        self.test_nonce = b"4662892146306485421546981092"
        self.test_nonce_hash = hashlib.sha256(self.test_nonce).hexdigest()
        self.test_code = "test-code"
        self.test_username = "test-username"
        self.test_username_invalid = "test-username@test.com"
        self.test_email = "test-email"
        self.test_sub = "test-sub"
        self.test_alt_username = "test-alt-username"
        self.test_alt_email = "test-alt-email"
        self.test_access_token = "test_access_token"
        self.test_refresh_token = "test_refresh_token"
        self.test_expires_in = 30
        self.test_refresh_expires_in = 1800
        self.test_user_id = str(uuid.uuid4())
        self.test_alt_user_id = str(uuid.uuid4())
        self.trans.request.url = (
            f"https://localhost:8000/authnz/custos/oidc/callback?state={self.test_state}&code={self.test_code}"
        )

    def setupMocks(self):
        self.mock_fetch_token(self.custos_authnz)
        self.mock_get_userinfo(self.custos_authnz)
        self.trans = self.mockTrans()

    @property
    def test_id_token(self):
        return unicodify(
            jwt.encode(
                {"nonce": self.test_nonce_hash, "aud": "test-client-id"},
                key="",
                algorithm="HS256",
            )
        )

    def mock_create_oauth2_session(self, custos_authnz):
        orig_create_oauth2_session = custos_authnz._create_oauth2_session

        def create_oauth2_session(state=None):
            self._create_oauth2_session_called = True
            assert state == self.test_state
            return orig_create_oauth2_session(state)

        custos_authnz._create_oauth2_session = create_oauth2_session

    def mock_fetch_token(self, custos_authnz):
        def fetch_token(oauth2_session, trans):
            self._fetch_token_called = True
            self._raw_token = {
                "access_token": self.test_access_token,
                "id_token": self.test_id_token,
                "refresh_token": self.test_refresh_token,
                "expires_in": self.test_expires_in,
                "refresh_expires_in": self.test_refresh_expires_in,
            }
            return self._raw_token

        custos_authnz._fetch_token = fetch_token

    def mock_get_userinfo(self, custos_authnz):
        def get_userinfo(oauth2_session):
            self._get_userinfo_called = True
            return {
                "preferred_username": self.test_username,
                "email": self.test_email,
                "sub": self.test_user_id,
                "alt_username": self.test_alt_username,
                "alt_email": self.test_alt_email,
                "alt_id": self.test_alt_user_id,
            }

        custos_authnz._get_userinfo = get_userinfo

    def mockRequest(self, request_dict):
        def get(x, **kwargs):
            assert x in request_dict
            return Response(request_dict[x])

        class Response:
            def __init__(self, resp):
                self.response = resp

            def json(self):
                return self.response

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
            external_user_id = None
            provider = None
            custos_authnz_token = None

            def filter_by(self, email=None, external_user_id=None, provider=None, username=None):
                self.external_user_id = external_user_id
                self.provider = provider
                if username:
                    # This is only called with a specific username to check if it
                    # already exists in the database.  Say no, for testing.
                    return QueryResult()
                if self.custos_authnz_token:
                    return QueryResult([self.custos_authnz_token])
                else:
                    return QueryResult()

        class Session:
            items = []
            flush_called = False
            _query = Query()
            deleted = []

            def add(self, item):
                self.items.append(item)

            def delete(self, item):
                self.deleted.append(item)

            def flush(self):
                self.flush_called = True

            def query(self, cls):
                return self._query

        class Trans(MockTrans):
            def __init__(self, app=None, user=None, history=None, **kwargs):
                super().__init__(app, user, history, **kwargs)
                self.cookies = {}
                self.cookies_args = {}
                self.request = Request()
                self.session = self.sa_session
                self.sa_session = Session()
                self.user = None

            def set_cookie(self, value, name=None, **kwargs):
                self.cookies[name] = value
                self.cookies_args[name] = kwargs

            def get_cookie(self, name):
                return self.cookies[name]

        return Trans()

    def tearDown(self):
        requests.get = self.orig_requests_get

    def test_parse_config(self):
        self.assertTrue(self.custos_authnz.config["verify_ssl"])
        self.assertEqual(self.custos_authnz.config["client_id"], "test-client-id")
        self.assertEqual(self.custos_authnz.config["client_secret"], "test-client-secret")
        self.assertEqual(self.custos_authnz.config["redirect_uri"], "https://test-redirect-uri")
        self.assertEqual(self.custos_authnz.config["authorization_endpoint"], "https://test-auth-endpoint")
        self.assertEqual(self.custos_authnz.config["token_endpoint"], "https://test-token-endpoint")
        self.assertEqual(self.custos_authnz.config["userinfo_endpoint"], "https://test-userinfo-endpoint")

    def test_authenticate_set_state_cookie(self):
        """Verify that authenticate() sets a state cookie."""
        authorization_url = self.custos_authnz.authenticate(self.trans)
        parsed = urlparse(authorization_url)
        state = parse_qs(parsed.query)["state"][0]
        self.assertEqual(state, self.trans.cookies[custos_authnz.STATE_COOKIE_NAME])

    def test_authenticate_set_nonce_cookie(self):
        """Verify that authenticate() sets a nonce cookie."""
        authorization_url = self.custos_authnz.authenticate(self.trans)
        parsed = urlparse(authorization_url)
        hashed_nonce_in_url = parse_qs(parsed.query)["nonce"][0]
        nonce_in_cookie = self.trans.cookies[custos_authnz.NONCE_COOKIE_NAME]
        hashed_nonce = self.custos_authnz._hash_nonce(nonce_in_cookie)
        self.assertEqual(hashed_nonce, hashed_nonce_in_url)

    def test_authenticate_set_pkce_verifier_cookie(self):
        try:
            import pkce  # noqa: F401
        except ImportError:
            raise SkipTest("pkce library is not available")
        """Verify that authenticate() sets a code verifier cookie."""
        self.custos_authnz.config["pkce_support"] = True
        authorization_url = self.custos_authnz.authenticate(self.trans)
        parsed = urlparse(authorization_url)
        code_challenge_in_url = parse_qs(parsed.query)["code_challenge"][0]
        verifier_in_cookie = self.trans.cookies[custos_authnz.VERIFIER_COOKIE_NAME]
        code_challenge_from_verifier = pkce.get_code_challenge(verifier_in_cookie)
        self.assertEqual(code_challenge_in_url, code_challenge_from_verifier)

    def test_authenticate_adds_extra_params(self):
        """Verify that authenticate() adds configured extra params."""
        authorization_url = self.custos_authnz.authenticate(self.trans)
        parsed = urlparse(authorization_url)
        param1_value = parse_qs(parsed.query)["kc_idp_hint"][0]
        self.assertEqual(param1_value, "oidc")

    def test_authenticate_sets_env_var_when_localhost_redirect(self):
        """Verify that OAUTHLIB_INSECURE_TRANSPORT var is set with localhost redirect."""
        self.custos_authnz = custos_authnz.CustosAuthnz(
            "Custos",
            {"VERIFY_SSL": True},
            {
                "url": self._get_idp_url(),
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
                "redirect_uri": "http://localhost/auth/callback",
                "realm": "test-realm",
            },
        )
        self.setupMocks()
        self.assertIsNone(os.environ.get("OAUTHLIB_INSECURE_TRANSPORT", None))
        self.custos_authnz.authenticate(self.trans)
        self.assertEqual("1", os.environ["OAUTHLIB_INSECURE_TRANSPORT"])

    def test_authenticate_does_not_set_env_var_when_https_redirect(self):
        self.assertTrue(self.custos_authnz.config["redirect_uri"].startswith("https:"))
        self.assertIsNone(os.environ.get("OAUTHLIB_INSECURE_TRANSPORT", None))
        self.custos_authnz.authenticate(self.trans)
        self.assertIsNone(os.environ.get("OAUTHLIB_INSECURE_TRANSPORT", None))

    def test_callback_verify_with_state_cookie(self):
        """Verify that state from cookie is passed to OAuth2Session constructor."""
        self.trans.set_cookie(value=self.test_state, name=custos_authnz.STATE_COOKIE_NAME)
        self.trans.set_cookie(value=self.test_nonce, name=custos_authnz.NONCE_COOKIE_NAME)
        old_access_token = "old-access-token"
        old_id_token = "old-id-token"
        old_refresh_token = "old-refresh-token"
        old_expiration_time = datetime.now() - timedelta(days=1)
        old_refresh_expiration_time = datetime.now() - timedelta(hours=3)
        existing_custos_authnz_token = CustosAuthnzToken(
            user=User(email=self.test_email, username=self.test_username),
            external_user_id=self.test_user_id,
            provider=self.custos_authnz.config["provider"],
            access_token=old_access_token,
            id_token=old_id_token,
            refresh_token=old_refresh_token,
            expiration_time=old_expiration_time,
            refresh_expiration_time=old_refresh_expiration_time,
        )

        self.trans.sa_session._query.custos_authnz_token = existing_custos_authnz_token
        self.assertIsNotNone(
            self.trans.sa_session.query(CustosAuthnzToken)
            .filter_by(external_user_id=self.test_user_id, provider=self.custos_authnz.config["provider"])
            .one_or_none()
        )
        self.trans.sa_session._query.user = User(email=self.test_email, username=self.test_username)

        # Mock _create_oauth2_session to make sure it is created with cookie state token
        self.mock_create_oauth2_session(self.custos_authnz)

        # Intentionally passing a bad state_token to make sure that code under
        # test uses the state cookie instead when creating the OAuth2Session
        login_redirect_url, user = self.custos_authnz.callback(
            state_token="xxx", authz_code=self.test_code, trans=self.trans, login_redirect_url="http://localhost:8000/"
        )
        self.assertTrue(self._create_oauth2_session_called)
        self.assertTrue(self._fetch_token_called)
        self.assertTrue(self._get_userinfo_called)
        self.assertEqual(login_redirect_url, "/")
        self.assertIsNotNone(user)

    def test_callback_nonce_validation_with_bad_nonce(self):
        self.trans.set_cookie(value=self.test_state, name=custos_authnz.STATE_COOKIE_NAME)
        self.trans.set_cookie(value=self.test_nonce, name=custos_authnz.NONCE_COOKIE_NAME)
        self.trans.sa_session._query.user = User(email=self.test_email, username=self.test_username)

        # Intentionally create a bad nonce
        self.test_nonce_hash = self.test_nonce_hash + "Z"

        # self.custos_authnz._fetch_token = fetch_token
        with self.assertRaisesRegex(Exception, "^Nonce mismatch"):
            self.custos_authnz.callback(
                state_token="xxx",
                authz_code=self.test_code,
                trans=self.trans,
                login_redirect_url="http://localhost:8000/",
            )
        self.assertTrue(self._fetch_token_called)
        self.assertFalse(self._get_userinfo_called)

    def test_callback_user_not_created_when_does_not_exists(self):
        self.trans.set_cookie(value=self.test_state, name=custos_authnz.STATE_COOKIE_NAME)
        self.trans.set_cookie(value=self.test_nonce, name=custos_authnz.NONCE_COOKIE_NAME)

        self.assertIsNone(
            self.trans.sa_session.query(CustosAuthnzToken)
            .filter_by(external_user_id=self.test_user_id, provider=self.custos_authnz.config["provider"])
            .one_or_none()
        )
        self.assertEqual(0, len(self.trans.sa_session.items))
        login_redirect_url, user = self.custos_authnz.callback(
            state_token="xxx", authz_code=self.test_code, trans=self.trans, login_redirect_url="http://localhost:8000/"
        )
        self.assertIsNone(user)
        self.assertTrue("http://localhost:8000/root/login?confirm=true&custos_token=" in login_redirect_url)
        self.assertTrue(self._fetch_token_called)

    def test_create_user(self):
        self.assertIsNone(
            self.trans.sa_session.query(CustosAuthnzToken)
            .filter_by(external_user_id=self.test_user_id, provider=self.custos_authnz.config["provider"])
            .one_or_none()
        )
        self.assertEqual(0, len(self.trans.sa_session.items))

        test_id_token = unicodify(
            jwt.encode(
                {
                    "nonce": self.test_nonce_hash,
                    "email": self.test_email,
                    "preferred_username": self.test_username_invalid,
                    "sub": self.test_sub,
                    "aud": "test-client-id",
                },
                key="",
                algorithm="HS256",
            )
        )

        self._raw_token = {
            "access_token": self.test_access_token,
            "id_token": test_id_token,
            "refresh_token": self.test_refresh_token,
            "expires_in": self.test_expires_in,
            "refresh_expires_in": self.test_refresh_expires_in,
        }
        login_redirect_url, user = self.custos_authnz.create_user(
            token=json.dumps(self._raw_token), trans=self.trans, login_redirect_url="http://localhost:8000/"
        )
        self.assertEqual(login_redirect_url, "http://localhost:8000/")
        self.trans.set_user(user)
        self.assertEqual(2, len(self.trans.sa_session.items), "Session has new User & new CustosAuthnzToken")
        added_user = self.trans.get_user()
        self.assertIsInstance(added_user, User)
        self.assertEqual(self.test_username, added_user.username)
        self.assertEqual(self.test_email, added_user.email)
        self.assertIsNotNone(added_user.password)
        # Verify added_custos_authnz_token
        added_custos_authnz_token = self.trans.sa_session.items[1]
        self.assertIsInstance(added_custos_authnz_token, CustosAuthnzToken)
        self.assertIs(user, added_custos_authnz_token.user)
        self.assertEqual(self.test_access_token, added_custos_authnz_token.access_token)
        self.assertEqual(test_id_token, added_custos_authnz_token.id_token)
        self.assertEqual(self.test_refresh_token, added_custos_authnz_token.refresh_token)
        expected_expiration_time = datetime.now() + timedelta(seconds=self.test_expires_in)
        expiration_timedelta = expected_expiration_time - added_custos_authnz_token.expiration_time
        self.assertTrue(expiration_timedelta.total_seconds() < 1)
        expected_refresh_expiration_time = datetime.now() + timedelta(seconds=self.test_refresh_expires_in)
        refresh_expiration_timedelta = (
            expected_refresh_expiration_time - added_custos_authnz_token.refresh_expiration_time
        )
        self.assertTrue(refresh_expiration_timedelta.total_seconds() < 1)
        self.assertEqual(self.custos_authnz.config["provider"], added_custos_authnz_token.provider)
        self.assertTrue(self.trans.sa_session.flush_called)

    def test_callback_galaxy_user_not_created_when_user_logged_in_and_no_custos_authnz_token_exists(self):
        """
        Galaxy user is already logged in and trying to associate external
        identity with their Galaxy user account. No new user should be created.
        """
        self.trans.set_cookie(value=self.test_state, name=custos_authnz.STATE_COOKIE_NAME)
        self.trans.set_cookie(value=self.test_nonce, name=custos_authnz.NONCE_COOKIE_NAME)
        self.trans.user = User()

        self.assertIsNone(
            self.trans.sa_session.query(CustosAuthnzToken)
            .filter_by(external_user_id=self.test_user_id, provider=self.custos_authnz.config["provider"])
            .one_or_none()
        )
        self.assertEqual(0, len(self.trans.sa_session.items))
        login_redirect_url, user = self.custos_authnz.callback(
            state_token="xxx", authz_code=self.test_code, trans=self.trans, login_redirect_url="http://localhost:8000/"
        )
        self.assertTrue(self._fetch_token_called)
        self.assertTrue(self._get_userinfo_called)
        self.assertEqual(1, len(self.trans.sa_session.items), "Session has new CustosAuthnzToken")
        # Verify added_custos_authnz_token
        added_custos_authnz_token = self.trans.sa_session.items[0]
        self.assertIsInstance(added_custos_authnz_token, CustosAuthnzToken)
        self.assertIs(user, added_custos_authnz_token.user)
        self.assertIs(user, self.trans.user)
        self.assertTrue(self.trans.sa_session.flush_called)

    def test_callback_galaxy_user_not_created_when_custos_authnz_token_exists(self):
        self.trans.set_cookie(value=self.test_state, name=custos_authnz.STATE_COOKIE_NAME)
        self.trans.set_cookie(value=self.test_nonce, name=custos_authnz.NONCE_COOKIE_NAME)
        old_access_token = "old-access-token"
        old_id_token = "old-id-token"
        old_refresh_token = "old-refresh-token"
        old_expiration_time = datetime.now() - timedelta(days=1)
        old_refresh_expiration_time = datetime.now() - timedelta(hours=3)
        existing_custos_authnz_token = CustosAuthnzToken(
            user=User(email=self.test_email, username=self.test_username),
            external_user_id=self.test_user_id,
            provider=self.custos_authnz.config["provider"],
            access_token=old_access_token,
            id_token=old_id_token,
            refresh_token=old_refresh_token,
            expiration_time=old_expiration_time,
            refresh_expiration_time=old_refresh_expiration_time,
        )

        self.trans.sa_session._query.custos_authnz_token = existing_custos_authnz_token

        self.assertIsNotNone(
            self.trans.sa_session.query(CustosAuthnzToken)
            .filter_by(external_user_id=self.test_user_id, provider=self.custos_authnz.config["provider"])
            .one_or_none()
        )
        self.assertEqual(0, len(self.trans.sa_session.items))
        login_redirect_url, user = self.custos_authnz.callback(
            state_token="xxx", authz_code=self.test_code, trans=self.trans, login_redirect_url="http://localhost:8000/"
        )
        self.assertTrue(self._fetch_token_called)
        self.assertTrue(self._get_userinfo_called)
        # Make sure query was called with correct parameters
        self.assertEqual(self.test_user_id, self.trans.sa_session._query.external_user_id)
        self.assertEqual(self.custos_authnz.config["provider"], self.trans.sa_session._query.provider)
        self.assertEqual(1, len(self.trans.sa_session.items), "Session has updated CustosAuthnzToken")
        session_custos_authnz_token = self.trans.sa_session.items[0]
        self.assertIsInstance(session_custos_authnz_token, CustosAuthnzToken)
        self.assertIs(
            existing_custos_authnz_token, session_custos_authnz_token, "existing CustosAuthnzToken should be updated"
        )
        # Verify both that existing CustosAuthnzToken has the correct values and different values than before
        self.assertEqual(self.test_access_token, session_custos_authnz_token.access_token)
        self.assertNotEqual(old_access_token, session_custos_authnz_token.access_token)
        self.assertEqual(self.test_id_token, session_custos_authnz_token.id_token)
        self.assertNotEqual(old_id_token, session_custos_authnz_token.id_token)
        self.assertEqual(self.test_refresh_token, session_custos_authnz_token.refresh_token)
        self.assertNotEqual(old_refresh_token, session_custos_authnz_token.refresh_token)
        expected_expiration_time = datetime.now() + timedelta(seconds=self.test_expires_in)
        expiration_timedelta = expected_expiration_time - session_custos_authnz_token.expiration_time
        self.assertTrue(expiration_timedelta.total_seconds() < 1)
        self.assertNotEqual(old_expiration_time, session_custos_authnz_token.expiration_time)
        expected_refresh_expiration_time = datetime.now() + timedelta(seconds=self.test_refresh_expires_in)
        refresh_expiration_timedelta = (
            expected_refresh_expiration_time - session_custos_authnz_token.refresh_expiration_time
        )
        self.assertTrue(refresh_expiration_timedelta.total_seconds() < 1)
        self.assertNotEqual(old_refresh_expiration_time, session_custos_authnz_token.refresh_expiration_time)
        self.assertTrue(self.trans.sa_session.flush_called)

    def test_disconnect(self):
        custos_authnz_token = CustosAuthnzToken(
            user=User(email=self.test_email, username=self.test_username),
            external_user_id=self.test_user_id,
            provider=self.custos_authnz.config["provider"],
            access_token=self.test_access_token,
            id_token=self.test_id_token,
            refresh_token=self.test_refresh_token,
            expiration_time=datetime.now() + timedelta(seconds=self.test_refresh_expires_in),
            refresh_expiration_time=datetime.now() + timedelta(seconds=self.test_refresh_expires_in),
        )
        self.trans.user = custos_authnz_token.user
        self.trans.user.custos_auth = [custos_authnz_token]
        provider = custos_authnz_token.provider
        email = custos_authnz_token.user.email

        success, message, redirect_uri = self.custos_authnz.disconnect(provider, self.trans, email, "/")

        self.assertEqual(1, len(self.trans.sa_session.deleted))
        deleted_token = self.trans.sa_session.deleted[0]
        self.assertIs(custos_authnz_token, deleted_token)
        self.assertTrue(self.trans.sa_session.flush_called)
        self.assertTrue(success)
        self.assertEqual("", message)
        self.assertEqual("/", redirect_uri)

    def test_disconnect_when_no_associated_provider(self):
        self.trans.user = User()
        success, message, redirect_uri = self.custos_authnz.disconnect("Custos", self.trans, "/")
        self.assertEqual(0, len(self.trans.sa_session.deleted))
        self.assertFalse(self.trans.sa_session.flush_called)
        self.assertFalse(success)
        self.assertNotEqual("", message)
        self.assertIsNone(redirect_uri)

    def test_disconnect_when_more_than_one_associated_token_for_provider(self):
        self.trans.user = User(email=self.test_email, username=self.test_username)
        custos_authnz_token1 = CustosAuthnzToken(
            user=self.trans.user,
            external_user_id=self.test_user_id + "1",
            provider=self.custos_authnz.config["provider"],
            access_token=self.test_access_token,
            id_token=self.test_id_token,
            refresh_token=self.test_refresh_token,
            expiration_time=datetime.now() + timedelta(seconds=self.test_refresh_expires_in),
            refresh_expiration_time=datetime.now() + timedelta(seconds=self.test_refresh_expires_in),
        )
        custos_authnz_token2 = CustosAuthnzToken(
            user=self.trans.user,
            external_user_id=self.test_user_id + "2",
            provider=self.custos_authnz.config["provider"],
            access_token=self.test_access_token,
            id_token=self.test_id_token,
            refresh_token=self.test_refresh_token,
            expiration_time=datetime.now() + timedelta(seconds=self.test_refresh_expires_in),
            refresh_expiration_time=datetime.now() + timedelta(seconds=self.test_refresh_expires_in),
        )
        self.trans.user.custos_auth = [custos_authnz_token1, custos_authnz_token2]

        success, message, redirect_uri = self.custos_authnz.disconnect("Custos", self.trans, "/")

        self.assertEqual(0, len(self.trans.sa_session.deleted))
        self.assertFalse(self.trans.sa_session.flush_called)
        self.assertFalse(success)
        self.assertNotEqual("", message)
        self.assertIsNone(redirect_uri)

    def test_logout_with_redirect(self):

        logout_redirect_url = "http://localhost:8080/post-logout"
        redirect_url = self.custos_authnz.logout(self.trans, logout_redirect_url)

        self.assertEqual(redirect_url, "https://test-end-session-endpoint?redirect_uri=" + quote(logout_redirect_url))
