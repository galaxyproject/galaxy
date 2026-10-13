import json
import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock
from urllib.parse import (
    parse_qs,
    urlencode,
    urlsplit,
)

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from social_core.backends.google_openidconnect import GoogleOpenIdConnect
from social_core.exceptions import AuthException
from sqlalchemy import event
from webob import Request

from galaxy import model
from galaxy.app_unittest_utils.galaxy_mock import MockTrans
from galaxy.authnz.flow_state import (
    FlowState,
    InvalidFlow,
)
from galaxy.authnz.keycloak import KeycloakOpenIdConnect
from galaxy.authnz.managers import AuthnzManager
from galaxy.authnz.psa_authnz import (
    _confirmation_identity,
    Storage,
    Strategy,
)
from galaxy.authnz.tapis import TapisOAuth2


@pytest.fixture
def trans(monkeypatch):
    trans = MockTrans()
    monkeypatch.setattr(trans.app.config, "enable_oidc", True, raising=False)
    monkeypatch.setattr(trans.app.config, "user_activation_on", False, raising=False)
    monkeypatch.setattr(trans.app.config, "oidc_auth_pipeline", None, raising=False)
    monkeypatch.setattr(trans.app.config, "oidc_auth_pipeline_extra", None, raising=False)
    trans.app.config.fixed_delegated_auth = False
    trans.galaxy_session = model.GalaxySession(is_valid=True)
    trans.sa_session.add(trans.galaxy_session)
    trans.sa_session.commit()
    monkeypatch.setattr(trans, "session", None, raising=False)
    trans.request = Request.blank("https://galaxy.example/authnz/keycloak/login")
    monkeypatch.setattr(trans.app.user_manager, "send_activation_email", Mock())
    manager = object.__new__(AuthnzManager)
    manager.app = trans.app
    manager.oidc_config = {"ID_TOKEN_MAX_AGE": 600, "VERIFY_SSL": True, "REQUESTS_TIMEOUT": 10}
    manager.oidc_backends_config = {
        "keycloak": {
            "client_id": "galaxy-client",
            "client_secret": "secret",
            "redirect_uri": "https://galaxy.example/authnz/keycloak/callback",
            "url": "https://idp.example",
            "require_create_confirmation": True,
            "pkce_support": True,
        }
    }
    manager.oidc_backends_implementation = {"keycloak": "psa"}
    trans.app.authnz_manager = manager
    yield trans
    trans.sa_session.close()


def adapter(trans):
    success, _, backend = trans.app.authnz_manager._get_authnz_backend("keycloak")
    assert success
    return backend


def pending(trans, **changes):
    data = {
        "email": "verified@example.com",
        "username": "Verified Name",
        "uid": "verified-subject",
        "response": {"access_token": "server-access", "refresh_token": "server-refresh"},
    }
    data.update(changes)
    return FlowState(trans.sa_session, trans.galaxy_session, "keycloak").save("confirmation", data)


def counts(trans):
    return tuple(trans.sa_session.query(cls).count() for cls in (model.User, model.Role, model.UserAuthnzToken))


@pytest.mark.parametrize("activation", [False, True])
def test_create_user_preserves_identity_tokens_and_activation(trans, activation):
    trans.app.config.user_activation_on = activation
    identifier = pending(trans)
    redirect, created_user = adapter(trans).create_user(identifier, trans, "/")
    assert redirect == "/"
    user = trans.sa_session.query(model.User).filter_by(email="verified@example.com").one()
    assert created_user is user
    assert user.active is not activation
    association = trans.sa_session.query(model.UserAuthnzToken).one()
    assert association.uid == "verified-subject"
    assert association.user_id == user.id
    assert association.extra_data["access_token"] == "server-access"
    assert trans.app.user_manager.send_activation_email.call_count == int(activation)


@pytest.mark.parametrize("invalid", ["logged_in", "disabled", "confirmation_disabled"])
def test_backend_rejects_confirmation_outside_registration(trans, invalid):
    identifier = pending(trans)
    if invalid == "logged_in":
        trans.set_user(trans.app.user_manager.create(email="existing@example.com", username="existing"))
    elif invalid == "disabled":
        trans.app.config.enable_oidc = False
    else:
        trans.app.authnz_manager.oidc_backends_config["keycloak"]["require_create_confirmation"] = False
    before = counts(trans)
    with pytest.raises(InvalidFlow):
        adapter(trans).create_user(identifier, trans, "/")
    assert counts(trans) == before


@pytest.mark.parametrize(
    "changes", [{"uid": None}, {"uid": ""}, {"uid": "None"}, {"email": []}, {"username": "!!!"}, {"response": []}]
)
def test_invalid_confirmation_identity(changes):
    data = {"email": "verified@example.com", "username": "verified", "uid": "subject", "response": {}}
    data.update(changes)
    with pytest.raises(InvalidFlow):
        _confirmation_identity(data)


@pytest.mark.parametrize("email", ["verified@example.com", "VERIFIED@example.com"])
def test_existing_email_cannot_be_linked(trans, email):
    identifier = pending(trans)
    trans.app.user_manager.create(email=email, username="existing")
    before = counts(trans)
    with pytest.raises(InvalidFlow):
        adapter(trans).create_user(identifier, trans, "/")
    assert counts(trans) == before


def test_existing_subject_cannot_be_linked(trans):
    identifier = pending(trans)
    existing = trans.app.user_manager.create(email="other@example.com", username="existing")
    trans.sa_session.add(model.UserAuthnzToken(user=existing, provider="keycloak", uid="verified-subject"))
    trans.sa_session.commit()
    before = counts(trans)
    with pytest.raises(InvalidFlow):
        adapter(trans).create_user(identifier, trans, "/")
    assert counts(trans) == before


@pytest.fixture(scope="module")
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def provider(trans, monkeypatch, signing_key):
    state = SimpleNamespace(nonce=None, claims={}, request_data=None, requests=[], bad_key=False, userinfo={})
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(signing_key.public_key()))
    jwk.update({"kid": "local-test", "alg": "RS256"})
    discovery = {
        "issuer": "https://idp.example",
        "authorization_endpoint": "https://idp.example/authorize",
        "token_endpoint": "https://idp.example/token",
        "userinfo_endpoint": "https://idp.example/userinfo",
        "jwks_uri": "https://idp.example/jwks",
    }

    def request(backend, url, *args, **kwargs):
        state.requests.append(url)
        data: dict[str, Any]
        if url.endswith("/.well-known/openid-configuration"):
            data = discovery
        elif url == discovery["jwks_uri"]:
            data = {"keys": [jwk]}
        elif url == discovery["token_endpoint"]:
            state.request_data = kwargs["data"]
            claims = {
                "iss": discovery["issuer"],
                "aud": "galaxy-client",
                "sub": "verified-subject",
                "email": "verified@example.com",
                "preferred_username": "verified",
                "iat": int(time.time()),
                "exp": int(time.time()) + 300,
                "nonce": state.nonce,
            }
            claims.update(state.claims)
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048) if state.bad_key else signing_key
            data = {
                "id_token": jwt.encode(claims, key, algorithm="RS256", headers={"kid": "local-test"}),
                "access_token": "opaque-access",
                "refresh_token": "opaque-refresh",
            }
        elif url == discovery["userinfo_endpoint"]:
            data = {"sub": "verified-subject", "email": "verified@example.com", "preferred_username": "verified"}
            data.update(state.userinfo)
        else:
            pytest.fail(f"Unexpected provider URL: {url}")
        return SimpleNamespace(json=lambda: data, text=json.dumps(data))

    monkeypatch.setattr(KeycloakOpenIdConnect, "request", request)
    # Cached discovery/JWKS methods must not reuse another test's fixtures.
    monkeypatch.setattr(KeycloakOpenIdConnect, "oidc_config", lambda backend: discovery)
    monkeypatch.setattr(KeycloakOpenIdConnect, "get_jwks_keys", lambda backend: [jwk])
    return state


def start(trans, provider):
    backend = adapter(trans)
    redirect = backend.authenticate(trans)
    query = parse_qs(urlsplit(redirect.url).query)
    provider.nonce = query["nonce"][0]
    return query


def callback(trans, query):
    trans.request = Request.blank(
        "https://galaxy.example/authnz/keycloak/callback?"
        + urlencode({"state": query["state"][0], "code": "local-code"})
    )
    return adapter(trans).callback(query["state"][0], "local-code", trans, "/")


@pytest.mark.parametrize("use_unique_user_id", [False, True])
def test_google_confirmation_preserves_backend_identity(trans, provider, monkeypatch, use_unique_user_id):
    manager = trans.app.authnz_manager
    manager.oidc_config["GOOGLE_OPENIDCONNECT_USE_UNIQUE_USER_ID"] = use_unique_user_id
    manager.oidc_backends_config["google"] = {
        **manager.oidc_backends_config["keycloak"],
        "redirect_uri": "https://galaxy.example/authnz/google/callback",
    }
    manager.oidc_backends_implementation["google"] = "psa"
    provider.claims["iss"] = "accounts.google.com"
    monkeypatch.setattr(GoogleOpenIdConnect, "oidc_config", KeycloakOpenIdConnect.oidc_config)
    monkeypatch.setattr(GoogleOpenIdConnect, "get_jwks_keys", KeycloakOpenIdConnect.get_jwks_keys)

    def request(backend, url, *args, **kwargs):
        provider_urls = {
            "https://accounts.google.com/o/oauth2/token": "https://idp.example/token",
            "https://openidconnect.googleapis.com/v1/userinfo": "https://idp.example/userinfo",
        }
        return KeycloakOpenIdConnect.request(backend, provider_urls.get(url, url), *args, **kwargs)

    monkeypatch.setattr(GoogleOpenIdConnect, "request", request)
    _, _, backend = manager._get_authnz_backend("google")
    query = parse_qs(urlsplit(backend.authenticate(trans).url).query)
    provider.nonce = query["nonce"][0]
    state = query["state"][0]
    trans.request = Request.blank(
        "https://galaxy.example/authnz/google/callback?" + urlencode({"state": state, "code": "local-code"})
    )
    _, _, backend = manager._get_authnz_backend("google")
    redirect, user = backend.callback(state, "local-code", trans, "/")
    assert user is None
    assert counts(trans) == (0, 0, 0)
    identifier = parse_qs(urlsplit(redirect).query)["confirmation_id"][0]
    _, user = backend.create_user(identifier, trans, "/")
    assert user.email == "verified@example.com"
    association = trans.sa_session.query(model.UserAuthnzToken).one()
    assert association.provider == "google-openidconnect"
    assert association.uid == ("verified-subject" if use_unique_user_id else "verified@example.com")
    assert association.user.email == "verified@example.com"


@pytest.mark.parametrize("invalid", ["signature", "subject", "state", "policy"])
def test_failed_callback_never_issues_confirmation(trans, provider, invalid, monkeypatch):
    query = start(trans, provider)
    if invalid == "signature":
        provider.bad_key = True
    elif invalid == "subject":
        provider.userinfo["sub"] = "another-subject"
    elif invalid == "state":
        query["state"] = ["wrong-state"]
    elif invalid == "policy":
        monkeypatch.setattr(KeycloakOpenIdConnect, "auth_allowed", lambda *args: False)
    with pytest.raises((InvalidFlow, AuthException)):
        callback(trans, query)
    assert counts(trans) == (0, 0, 0)
    assert trans.sa_session.query(model.PSAPartial).filter_by(next_step=-2).count() == 0
    if invalid == "state":
        assert not provider.requests


def test_oauth2_callback_and_confirmation_without_id_token(trans, monkeypatch):
    manager = trans.app.authnz_manager
    manager.oidc_backends_config["tapis"] = {
        "client_id": "galaxy-client",
        "client_secret": "secret",
        "tenant_id": "tacc",
        "redirect_uri": "https://galaxy.example/authnz/tapis/callback",
        "require_create_confirmation": True,
    }
    manager.oidc_backends_implementation["tapis"] = "psa"

    def get_json(backend, url, **kwargs):
        if url.endswith("/tokens"):
            assert kwargs["data"]["code"] == "local-code"
            return {"result": {"access_token": {"access_token": "opaque"}, "refresh_token": "refresh"}}
        assert url.endswith("/userinfo")
        assert kwargs["headers"]["X-Tapis-Token"] == "opaque"
        return {"result": {"username": "oauth-user"}}

    monkeypatch.setattr(TapisOAuth2, "get_json", get_json)
    success, _, backend = manager._get_authnz_backend("tapis")
    assert success
    redirect = backend.authenticate(trans)
    state = parse_qs(urlsplit(redirect.url).query)["state"][0]
    trans.request = Request.blank(
        "https://galaxy.example/authnz/tapis/callback?" + urlencode({"state": state, "code": "local-code"})
    )
    success, _, backend = manager._get_authnz_backend("tapis")
    assert success
    redirect, user = backend.callback(state, "local-code", trans, "/")
    assert user is None
    assert counts(trans) == (0, 0, 0)
    identifier = parse_qs(urlsplit(redirect).query)["confirmation_id"][0]
    _, user = backend.create_user(identifier, trans, "/")
    assert user is not None
    assert trans.sa_session.query(model.UserAuthnzToken).one().uid == "tacc:oauth-user"


def test_strategy_preserves_empty_session():
    session: dict[str, str] = {}
    strategy = Strategy(None, session, Storage, {})
    strategy.session_set("pkce_code_verifier", "secret")
    assert session == {"pkce_code_verifier": "secret"}
    assert strategy.session_pop("pkce_code_verifier") == "secret"
    assert session == {}


def test_backend_alias_uses_canonical_confirmation_binding(trans):
    manager = trans.app.authnz_manager
    manager.oidc_backends_config["google"] = manager.oidc_backends_config["keycloak"]
    manager.oidc_backends_implementation["google"] = "psa"
    identifier = FlowState(trans.sa_session, trans.galaxy_session, "google").save(
        "confirmation",
        {"email": "verified@example.com", "username": "verified", "uid": "google-sub", "response": {}},
    )
    success, _, (_, user) = manager.create_user("google-openidconnect", identifier, trans, "/")
    assert success
    assert user is not None
    assert trans.sa_session.query(model.UserAuthnzToken).one().provider == "google-openidconnect"


def test_association_failure_cannot_reuse_confirmation(trans):
    identifier = pending(trans)

    def fail_association(session, flush_context, instances):
        if any(isinstance(obj, model.UserAuthnzToken) for obj in session.new):
            raise RuntimeError("Simulated association storage failure")

    event.listen(trans.sa_session, "before_flush", fail_association)
    try:
        with pytest.raises(RuntimeError, match="Simulated association storage failure"):
            adapter(trans).create_user(identifier, trans, "/")
    finally:
        event.remove(trans.sa_session, "before_flush", fail_association)
    # UserManager commits the account/private role before the association. This
    # existing transaction boundary must not make the consumed confirmation reusable.
    assert counts(trans) == (1, 1, 0)
    with pytest.raises(InvalidFlow):
        adapter(trans).create_user(identifier, trans, "/")
