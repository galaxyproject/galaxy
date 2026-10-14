import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from webob import Request

from galaxy.authnz.flow_state import InvalidFlow
from galaxy.authnz.managers import AuthnzManager
from galaxy.web.framework.base import Response
from galaxy.webapps.base.webapp import GalaxyWebTransaction
from galaxy.webapps.galaxy.controllers.authnz import OIDC


@pytest.fixture
def trans(monkeypatch):
    trans = SimpleNamespace(
        app=SimpleNamespace(
            config=SimpleNamespace(enable_oidc=True),
            authnz_manager=Mock(spec=AuthnzManager),
        ),
        user=None,
        session_csrf_token="csrf",
        response=Response(),
        handle_user_login=Mock(),
        set_cookie=Mock(),
    )
    trans.check_csrf_token = GalaxyWebTransaction.check_csrf_token.__get__(trans)
    monkeypatch.setattr("galaxy.webapps.galaxy.controllers.authnz.url_for", lambda path: path)
    return trans


def request(trans, action, *, method="POST", csrf="csrf", **kwargs):
    fields = {"confirmation_id": "pending", "session_csrf_token": csrf, **kwargs}
    trans.request = Request.blank(
        f"/authnz/keycloak/{action}", method=method, POST=fields if method == "POST" else None
    )
    controller = object.__new__(OIDC)
    return json.loads(getattr(controller, action)(trans, "keycloak", **fields))


@pytest.mark.parametrize("action", ["create_user", "cancel_user_creation"])
@pytest.mark.parametrize("method,csrf,status", [("GET", "csrf", 405), ("POST", "", 403), ("POST", "wrong", 403)])
def test_confirmation_guards_reject_before_calling_manager(trans, action, method, csrf, status):
    result = request(trans, action, method=method, csrf=csrf)
    assert trans.response.status == status
    assert trans.response.get_content_type() == "application/json"
    assert trans.response.headers["Cache-Control"] == "no-store"
    assert "err_msg" in result
    if method == "GET":
        assert trans.response.headers["Allow"] == "POST"
    assert trans.app.authnz_manager.mock_calls == []
    trans.handle_user_login.assert_not_called()


@pytest.mark.parametrize("parameter", ["token", "provider_token", "callback", "jsonp"])
def test_confirmation_rejects_legacy_credentials_and_jsonp(trans, parameter):
    result = request(trans, "create_user", **{parameter: "untrusted"})
    assert trans.response.status == 400
    assert "err_msg" in result
    assert trans.app.authnz_manager.mock_calls == []
    trans.handle_user_login.assert_not_called()


@pytest.mark.parametrize("context", ["logged_in", "disabled"])
def test_confirmation_rejects_invalid_registration_context(trans, context):
    if context == "logged_in":
        trans.user = object()
    else:
        trans.app.config.enable_oidc = False
    result = request(trans, "create_user")
    assert trans.response.status == 400
    assert "err_msg" in result
    assert trans.app.authnz_manager.mock_calls == []


def test_invalid_confirmation_returns_error_without_login(trans):
    trans.app.authnz_manager.create_user.side_effect = InvalidFlow()
    result = request(trans, "create_user")
    assert trans.response.status == 400
    assert "err_msg" in result
    trans.handle_user_login.assert_not_called()
    trans.set_cookie.assert_not_called()


def test_cancellation_returns_empty_response_without_login(trans):
    result = request(trans, "cancel_user_creation")
    assert trans.response.status == 200
    assert result == {}
    trans.app.authnz_manager.cancel_user_creation.assert_called_once_with("keycloak", "pending", trans)
    trans.handle_user_login.assert_not_called()
