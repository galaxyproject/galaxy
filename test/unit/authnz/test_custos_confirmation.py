import json
import time
from datetime import (
    datetime,
    timedelta,
)
from unittest.mock import Mock
from urllib.parse import (
    parse_qs,
    urlsplit,
)

import jwt
import pytest
from webob import Request

from galaxy import model
from galaxy.app_unittest_utils.galaxy_mock import MockTrans
from galaxy.authnz.custos_authnz import OIDCAuthnzBase
from galaxy.authnz.flow_state import (
    authentication_id,
    FlowState,
    InvalidFlow,
)


@pytest.fixture
def trans(monkeypatch):
    trans = MockTrans()
    monkeypatch.setattr(trans.app.config, "enable_oidc", True, raising=False)
    monkeypatch.setattr(trans.app.config, "user_activation_on", False, raising=False)
    trans.app.config.fixed_delegated_auth = False
    trans.galaxy_session = model.GalaxySession(is_valid=True)
    trans.sa_session.add(trans.galaxy_session)
    trans.sa_session.commit()
    trans.request = Request.blank("https://galaxy.example/authnz/keycloak/login")
    monkeypatch.setattr(trans.app.user_manager, "send_activation_email", Mock())
    yield trans
    trans.sa_session.close()


@pytest.fixture
def backend():
    backend = OIDCAuthnzBase(
        "Keycloak",
        {"VERIFY_SSL": True},
        {
            "url": "https://idp.example",
            "client_id": "galaxy-client",
            "client_secret": "secret",
            "redirect_uri": "https://galaxy.example/authnz/keycloak/callback",
            "require_create_confirmation": True,
            "pkce_support": True,
        },
    )
    backend.config.issuer = "https://idp.example"
    backend.config.authorization_endpoint = "https://idp.example/authorize"
    return backend


def pending(trans):
    return FlowState(trans.sa_session, trans.galaxy_session, "keycloak").save(
        "confirmation",
        {
            "email": "verified@example.com",
            "username": "verified",
            "user_id": "verified-subject",
            "access_token": "server-access",
            "id_token": "server-id",
            "refresh_token": "server-refresh",
            "expiration_time": (datetime.now() + timedelta(minutes=5)).isoformat(),
            "refresh_expiration_time": None,
        },
    )


def counts(trans):
    return tuple(trans.sa_session.query(cls).count() for cls in (model.User, model.Role, model.CustosAuthnzToken))


def test_browser_supplied_identity_is_never_accepted(trans, backend):
    forged = json.dumps(
        {
            "access_token": "forged",
            "id_token": jwt.encode(
                {
                    "email": "attacker@example.com",
                    "sub": "forged-subject",
                    "preferred_username": "attacker",
                },
                "attacker",
                algorithm="HS256",
            ),
        }
    )
    before = counts(trans)
    with pytest.raises(InvalidFlow):
        backend.create_user(forged, trans, "/")
    assert counts(trans) == before


@pytest.mark.parametrize("activation", [False, True])
def test_confirmation_preserves_identity_tokens_and_activation(trans, backend, activation):
    trans.app.config.user_activation_on = activation
    identifier = pending(trans)
    redirect, user = backend.create_user(identifier, trans, "/")
    assert redirect == "/"
    assert user.email == "verified@example.com"
    assert user.active is not activation
    association = trans.sa_session.query(model.CustosAuthnzToken).one()
    assert association.external_user_id == "verified-subject"
    assert association.provider == "keycloak"
    assert association.user_id == user.id
    assert association.access_token == "server-access"
    assert association.id_token == "server-id"
    assert association.refresh_token == "server-refresh"
    assert association.refresh_expiration_time is None
    assert trans.app.user_manager.send_activation_email.call_count == int(activation)
    with pytest.raises(InvalidFlow):
        backend.create_user(identifier, trans, "/")


@pytest.mark.parametrize("context", ["logged_in", "disabled", "confirmation_disabled"])
def test_confirmation_requires_registration_context(trans, backend, context):
    identifier = pending(trans)
    if context == "logged_in":
        trans.set_user(trans.app.user_manager.create(email="existing@example.com", username="existing"))
    elif context == "disabled":
        trans.app.config.enable_oidc = False
    else:
        backend.config.require_create_confirmation = False
    before = counts(trans)
    for action in (backend.create_user, backend.cancel_user_creation):
        with pytest.raises(InvalidFlow):
            if action == backend.create_user:
                action(identifier, trans, "/")
            else:
                action(identifier, trans)
    assert counts(trans) == before


@pytest.mark.parametrize("collision", ["email", "email_case", "subject"])
def test_identity_collision_consumes_confirmation_without_linking(trans, backend, collision):
    identifier = pending(trans)
    email = {"email": "verified@example.com", "email_case": "VERIFIED@example.com", "subject": "other@example.com"}[
        collision
    ]
    user = trans.app.user_manager.create(email=email, username="existing")
    if collision == "subject":
        trans.sa_session.add(
            model.CustosAuthnzToken(user=user, provider="keycloak", external_user_id="verified-subject")
        )
        trans.sa_session.commit()
    before = counts(trans)
    with pytest.raises(InvalidFlow):
        backend.create_user(identifier, trans, "/")
    assert counts(trans) == before
    with pytest.raises(InvalidFlow):
        backend.cancel_user_creation(identifier, trans)


def test_creation_failure_cannot_be_retried(trans, backend, monkeypatch):
    identifier = pending(trans)
    monkeypatch.setattr(trans.app.user_manager, "create", Mock(side_effect=RuntimeError("creation failed")))
    with pytest.raises(RuntimeError, match="creation failed"):
        backend.create_user(identifier, trans, "/")
    trans.sa_session.rollback()
    with pytest.raises(InvalidFlow):
        backend.create_user(identifier, trans, "/")


def test_authentication_keeps_nonce_and_pkce_server_side(trans, backend):
    query = parse_qs(urlsplit(backend.authenticate(trans)).query)
    data = FlowState(trans.sa_session, trans.galaxy_session, "keycloak").consume(
        "authentication", authentication_id(query["state"][0])
    )
    assert data["nonce"] == query["nonce"][0]
    assert data["code_verifier"]
    assert data["code_verifier"] not in str(query)
    assert query["code_challenge_method"] == ["S256"]


def test_callback_failure_consumes_state_before_exchange(trans, backend, monkeypatch):
    query = parse_qs(urlsplit(backend.authenticate(trans)).query)
    exchange = Mock(side_effect=RuntimeError("exchange failed"))
    monkeypatch.setattr(backend, "_fetch_token", exchange)
    with pytest.raises(RuntimeError, match="exchange failed"):
        backend.callback(query["state"][0], "code", trans, "/")
    with pytest.raises(InvalidFlow):
        backend.callback(query["state"][0], "code", trans, "/")
    assert exchange.call_count == 1


@pytest.mark.parametrize(
    "change",
    [
        {"nonce": "wrong"},
        {"exp": 1},
        {"aud": "other-client"},
        {"iss": "other-issuer"},
        {"sub": ""},
        {"email": []},
    ],
)
def test_callback_rejects_invalid_identity(trans, backend, change):
    claims = {
        "email": "verified@example.com",
        "sub": "subject",
        "aud": "galaxy-client",
        "iss": "https://idp.example",
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
        "nonce": "expected",
    }
    claims.update(change)
    token = {"access_token": "access", "id_token": jwt.encode(claims, "provider", algorithm="HS256")}
    oauth = Mock()
    oauth.get.return_value.json.return_value = {"sub": "different-subject", "email": "verified@example.com"}
    with pytest.raises((InvalidFlow, jwt.InvalidTokenError)):
        backend._process_token(trans, oauth, token, nonce="expected")


def test_userinfo_must_match_authenticated_subject(trans, backend):
    claims = {
        "sub": "subject",
        "aud": "galaxy-client",
        "iss": "https://idp.example",
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
        "nonce": "expected",
    }
    token = {"access_token": "access", "id_token": jwt.encode(claims, "provider", algorithm="HS256")}
    oauth = Mock()
    oauth.get.return_value.json.return_value = {"sub": "other-subject", "email": "verified@example.com"}
    with pytest.raises(InvalidFlow):
        backend._process_token(trans, oauth, token, nonce="expected")
