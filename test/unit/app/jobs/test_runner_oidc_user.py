from types import SimpleNamespace

import jwt
import pytest

from galaxy.exceptions import ConfigurationError
from galaxy.jobs.oidc_user import (
    configure_destination,
    OidcUsernameError,
    validate_destination,
)

TOKEN_SECRET = "unit-test-signing-key-at-least-32-bytes"


def _token(claims):
    return jwt.encode(claims, TOKEN_SECRET, algorithm="HS256")


def _configure(tokens, providers=None, **destination_params):
    params = {
        "docker_enabled": True,
        "docker_username_from_oidc_token_claim": {
            "set_user": True,
            "providers": providers or {"oidc": {"claim": "preferred_username"}},
        },
        **destination_params,
    }
    user = SimpleNamespace(get_oidc_tokens=tokens if callable(tokens) else lambda backend: tokens)
    wrapper = SimpleNamespace(
        job_destination=SimpleNamespace(params=params), get_job=lambda: SimpleNamespace(user=user)
    )
    configure_destination(wrapper)
    return params


@pytest.mark.parametrize(
    "access",
    [
        None,
        "opaque-access-token",
        _token({"scope": "openid"}),
        _token({"preferred_username": 123}),
        _token({"preferred_username": ""}),
    ],
)
def test_id_token_fallback_when_access_cannot_supply_identity(access):
    params = _configure({"access": access, "id": _token({"preferred_username": "alice"})})
    assert params["docker_username_from_token"] == "alice"


def test_access_token_identity_retains_precedence():
    params = _configure(
        {"access": _token({"preferred_username": "alice"}), "id": _token({"preferred_username": "bob"})}
    )
    assert params["docker_username_from_token"] == "alice"


def test_id_token_fallback_when_access_identity_does_not_match_template():
    params = _configure(
        {"access": _token({"preferred_username": "other"}), "id": _token({"preferred_username": "alice@example.org"})},
        providers={"oidc": {"claim": "preferred_username", "template": "alice"}},
    )
    assert params["docker_username_from_token"] == "alice"


def test_no_usable_identity_fails():
    with pytest.raises(OidcUsernameError, match="Failed to get a username"):
        _configure({"access": "opaque-access-token", "id": _token({"scope": "openid"})})


def test_job_without_a_user_fails():
    wrapper = SimpleNamespace(
        job_destination=SimpleNamespace(
            params={
                "docker_enabled": True,
                "docker_username_from_oidc_token_claim": {
                    "set_user": True,
                    "providers": {"oidc": {"claim": "preferred_username"}},
                },
            }
        ),
        get_job=lambda: SimpleNamespace(user=None),
    )
    with pytest.raises(OidcUsernameError, match="job has no user"):
        configure_destination(wrapper)


@pytest.mark.parametrize(
    "claim,template",
    [
        ("alice@example.org", r"^([a-z_][a-z0-9_-]*)@example\.org$"),
        ("alice42", r"^(alice|bob)[0-9]+$"),
        ("alice", r"^(bob)?alice$"),
    ],
)
def test_template_capture_groups_preserve_the_whole_match(claim, template):
    params = _configure(
        {"id": _token({"unique_name": claim})},
        providers={"oidc": {"claim": "unique_name", "template": template}},
    )
    assert params["docker_username_from_token"] == claim


def test_template_without_a_capture_group_uses_the_whole_match():
    params = _configure(
        {"id": _token({"unique_name": "alice@example.org"})},
        providers={"oidc": {"claim": "unique_name", "template": "^[a-z_][a-z0-9_-]*"}},
    )
    assert params["docker_username_from_token"] == "alice"


def test_template_that_cannot_match_falls_through_to_failure():
    with pytest.raises(OidcUsernameError):
        _configure(
            {"id": _token({"unique_name": "alice@example.org"})},
            providers={"oidc": {"claim": "unique_name", "template": r"^([0-9]+)@example\.org$"}},
        )


def test_explicit_docker_user_conflicts_with_token_user():
    with pytest.raises(ConfigurationError, match="docker_set_user cannot be used together"):
        _configure({"id": _token({"preferred_username": "alice"})}, docker_set_user="1000:1000")


@pytest.mark.parametrize("set_user", [False, "false", "False", "0"])
def test_env_only_boolean_does_not_conflict_with_explicit_docker_user(set_user):
    params = _configure(
        {"id": _token({"preferred_username": "alice"})},
        docker_set_user="1000:1000",
        docker_username_from_oidc_token_claim={
            "set_user": set_user,
            "expose_as_env": "GALAXY_TOOL_USER",
            "providers": {"oidc": {"claim": "preferred_username"}},
        },
    )
    assert params["docker_username_from_token"] == "alice"


@pytest.mark.parametrize("config", [None, {}, {"set_user": "false"}, {"set_user": False, "providers": {}}])
def test_disabled_identity_does_not_read_tokens(config):
    def unexpected_token_lookup(backend):
        pytest.fail("Disabled identity configuration must not read user tokens")

    params = _configure(unexpected_token_lookup, docker_username_from_oidc_token_claim=config)
    assert "docker_username_from_token" not in params


@pytest.mark.parametrize(
    "config",
    [
        "true",
        {"set_user": "not-a-boolean"},
        {"set_user": True},
        {"set_user": True, "providers": {}},
        {"set_user": True, "providers": ["oidc"]},
        {"set_user": True, "providers": {"unknown": {"claim": "name"}}},
        {"set_user": True, "providers": {"oidc": "name"}},
        {"set_user": True, "providers": {"oidc": {}}},
        {"set_user": True, "providers": {"oidc": {"claim": 123}}},
        {"set_user": True, "providers": {"oidc": {"claim": ""}}},
        {"set_user": True, "providers": {"oidc": {"claim": "name", "template": "["}}},
        {"set_user": True, "providers": {"oidc": {"claim": "name", "template": None}}},
        {"expose_as_env": "INVALID=NAME"},
        {"expose_as_env": 123},
        {"expose_as_env": "INVALID NAME"},
    ],
)
def test_invalid_identity_configuration_fails_clearly(config):
    with pytest.raises(ConfigurationError):
        _configure({}, docker_username_from_oidc_token_claim=config)


def test_provider_order_precedes_token_kind_and_later_provider_is_not_read():
    requested = []

    def get_tokens(backend):
        requested.append(backend)
        assert backend == "oidc"
        return {"access": "opaque", "id": _token({"preferred_username": "alice"})}

    params = _configure(
        get_tokens,
        providers={"oidc": {"claim": "preferred_username"}, "keycloak": {"claim": "preferred_username"}},
    )
    assert params["docker_username_from_token"] == "alice"
    assert requested == ["oidc"]


def test_provider_lookup_failure_tries_next_configured_provider():
    requested = []

    def get_tokens(backend):
        requested.append(backend)
        if backend == "oidc":
            raise RuntimeError("Unavailable provider")
        return {"id": _token({"preferred_username": "bob"})}

    params = _configure(
        get_tokens,
        providers={"oidc": {"claim": "preferred_username"}, "keycloak": {"claim": "preferred_username"}},
    )
    assert params["docker_username_from_token"] == "bob"
    assert requested == ["oidc", "keycloak"]


def test_identity_requires_a_docker_destination():
    """The container layer only honors this on Docker destinations - do not silently no-op."""
    with pytest.raises(ConfigurationError, match="requires docker_enabled"):
        _configure({"id": _token({"preferred_username": "alice"})}, docker_enabled=False)


def test_startup_validation_reports_the_destination():
    with pytest.raises(ConfigurationError, match=r"Invalid destination \[docker_oidc\]"):
        validate_destination(
            "docker_oidc",
            {
                "docker_enabled": True,
                "docker_username_from_oidc_token_claim": {"set_user": True, "providers": {"nope": {"claim": "sub"}}},
            },
        )


def test_startup_validation_accepts_a_valid_destination():
    validate_destination(
        "docker_oidc",
        {
            "docker_enabled": True,
            "docker_username_from_oidc_token_claim": {
                "set_user": True,
                "providers": {"azure": {"claim": "unique_name", "template": "^[a-z_][a-z0-9_-]*"}},
            },
        },
    )
