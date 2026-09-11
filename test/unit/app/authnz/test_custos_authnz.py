import hashlib
import os
import uuid
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    cast,
    Optional,
    TYPE_CHECKING,
)
from urllib.parse import (
    quote,
)

import jwt

from galaxy.app_unittest_utils.galaxy_mock import MockTrans
from galaxy.authnz import custos_authnz
from galaxy.model import (
    CustosAuthnzToken,
    User,
)
from galaxy.util import (
    requests,
    unicodify,
)
from galaxy.util.unittest import TestCase

if TYPE_CHECKING:
    from sqlalchemy.orm import scoped_session

# CustosAuthnz decodes ID tokens without verifying the signature, so any key works.
TEST_ID_TOKEN_KEY = "test-id-token-signing-key-0123456"


class TestCustosAuthnz(TestCase):
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
        self.custos_authnz = custos_authnz.CustosAuthFactory.GetCustosBasedAuthProvider(
            "Custos",
            {"VERIFY_SSL": True},
            {
                "url": self._get_idp_url(),
                "client_id": "test-client-id",
                "client_secret": "test-client-secret",
                "redirect_uri": "https://test-redirect-uri",
                "realm": "test-realm",
                "label": "test-identity-provider",
                "require_create_confirmation": False,
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
        self.trans.app.config.enable_oidc = True
        self.trans.app.config.oidc = []
        self.trans.app.auth_manager.authenticators = []
        self.trans.app.config.fixed_delegated_auth = False

    @property
    def test_id_token(self):
        return unicodify(
            jwt.encode(
                {"nonce": self.test_nonce_hash, "aud": "test-client-id"},
                key=TEST_ID_TOKEN_KEY,
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
            custos_authnz_token: Optional[CustosAuthnzToken] = None

            def filter_by(self, email=None, external_user_id=None, provider=None, username=None):
                self.external_user_id = external_user_id
                self.provider = provider
                if username:
                    # This is only called with a specific username to check if it
                    # already exists in the database.  For testing, return none except for one username.
                    return QueryResult()
                if email == "existing@example.com":
                    user = User(email=email, username="test-user")
                    return QueryResult([user])
                if self.custos_authnz_token:
                    return QueryResult([self.custos_authnz_token])
                else:
                    return QueryResult()

        class Session:
            items = []
            commit_called = False
            _query = Query()
            deleted = []

            def add(self, item):
                self.items.append(item)

            def delete(self, item):
                self.deleted.append(item)

            def commit(self):
                self.commit_called = True

            def query(self, cls):
                return self._query

        class Trans(MockTrans):
            def __init__(self, app=None, user=None, history=None, **kwargs):
                super().__init__(app, user, history, **kwargs)
                self.cookies = {}
                self.cookies_args = {}
                self.request = Request()
                self.sa_session = cast("scoped_session", Session())
                self.user = None

            def set_cookie(self, value, name=None, **kwargs):
                self.cookies[name] = value
                self.cookies_args[name] = kwargs

            def get_cookie(self, name):
                return self.cookies[name]

        return Trans()

    def tearDown(self):
        requests.get = self.orig_requests_get
        os.environ.pop("OAUTHLIB_INSECURE_TRANSPORT", None)

    def test_parse_config(self):
        assert self.custos_authnz.config.verify_ssl
        assert self.custos_authnz.config.client_id == "test-client-id"
        assert self.custos_authnz.config.client_secret == "test-client-secret"
        assert self.custos_authnz.config.redirect_uri == "https://test-redirect-uri"
        assert self.custos_authnz.config.authorization_endpoint == "https://test-auth-endpoint"
        assert self.custos_authnz.config.token_endpoint == "https://test-token-endpoint"
        assert self.custos_authnz.config.userinfo_endpoint == "https://test-userinfo-endpoint"
        assert self.custos_authnz.config.label == "test-identity-provider"
        assert self.custos_authnz.config.require_create_confirmation is False

    def test_disconnect(self):
        custos_authnz_token = CustosAuthnzToken(
            user=User(email=self.test_email, username=self.test_username),
            external_user_id=self.test_user_id,
            provider=self.custos_authnz.config.provider,
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

        success, message, redirect_uri = self.custos_authnz.disconnect(
            provider,
            self.trans,
            disconnect_redirect_url="/",
            email=email,
        )

        assert 1 == len(self.trans.sa_session.deleted)
        deleted_token = self.trans.sa_session.deleted[0]
        assert custos_authnz_token is deleted_token
        assert self.trans.sa_session.commit_called
        assert success
        assert "" == message
        assert "/" == redirect_uri

    def test_disconnect_when_no_associated_provider(self):
        self.trans.user = User()
        success, message, redirect_uri = self.custos_authnz.disconnect("Custos", self.trans, "/")
        assert 0 == len(self.trans.sa_session.deleted)
        assert not self.trans.sa_session.commit_called
        assert not success
        assert "" != message
        assert redirect_uri is None

    def test_disconnect_when_more_than_one_associated_token_for_provider(self):
        self.trans.user = User(email=self.test_email, username=self.test_username)
        custos_authnz_token1 = CustosAuthnzToken(
            user=self.trans.user,
            external_user_id=self.test_user_id + "1",
            provider=self.custos_authnz.config.provider,
            access_token=self.test_access_token,
            id_token=self.test_id_token,
            refresh_token=self.test_refresh_token,
            expiration_time=datetime.now() + timedelta(seconds=self.test_refresh_expires_in),
            refresh_expiration_time=datetime.now() + timedelta(seconds=self.test_refresh_expires_in),
        )
        custos_authnz_token2 = CustosAuthnzToken(
            user=self.trans.user,
            external_user_id=self.test_user_id + "2",
            provider=self.custos_authnz.config.provider,
            access_token=self.test_access_token,
            id_token=self.test_id_token,
            refresh_token=self.test_refresh_token,
            expiration_time=datetime.now() + timedelta(seconds=self.test_refresh_expires_in),
            refresh_expiration_time=datetime.now() + timedelta(seconds=self.test_refresh_expires_in),
        )
        self.trans.user.custos_auth = [custos_authnz_token1, custos_authnz_token2]

        success, message, redirect_uri = self.custos_authnz.disconnect("Custos", self.trans, "/")

        assert 0 == len(self.trans.sa_session.deleted)
        assert not self.trans.sa_session.commit_called
        assert not success
        assert "" != message
        assert redirect_uri is None

    def test_logout_with_redirect(self):
        logout_redirect_url = "http://localhost:8080/post-logout"
        redirect_url = self.custos_authnz.logout(self.trans, logout_redirect_url)

        assert redirect_url == "https://test-end-session-endpoint?redirect_uri=" + quote(logout_redirect_url)
