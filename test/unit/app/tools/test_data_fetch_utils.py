from datetime import (
    datetime,
    timedelta,
    timezone,
)
from types import SimpleNamespace
from typing import cast

from galaxy.model import User
from galaxy.schema.drs import ContentsObject
from galaxy.tools.data_fetch import UploadConfig
from galaxy.tools.data_fetch_utils import (
    _drs_contents_to_items,
    compute_token_expiry_for_provider,
    drs_bundle_to_items,
)


class DummyToken:
    def __init__(self, provider, expiration_time):
        self.provider = provider
        now_ts = int(datetime.now(timezone.utc).timestamp())
        self.extra_data = {
            "auth_time": now_ts,
            "expires": int(expiration_time.timestamp()) - now_ts,
        }


class DummyUser:
    def __init__(self, social_auth):
        self.social_auth = social_auth


def _truncate_to_seconds(value: datetime) -> datetime:
    return value.replace(microsecond=0)


def test_compute_token_expiry_for_provider_returns_none_for_no_user():
    assert compute_token_expiry_for_provider(None, "oidc") is None


def test_compute_token_expiry_for_provider_returns_none_for_empty_social_auth():
    assert compute_token_expiry_for_provider(cast(User, DummyUser([])), "oidc") is None


def test_compute_token_expiry_for_provider_returns_expiry_for_matching_provider():
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    user = DummyUser([DummyToken("oidc", expiry)])
    assert compute_token_expiry_for_provider(cast(User, user), "oidc") == _truncate_to_seconds(expiry)


def test_compute_token_expiry_for_provider_ignores_other_providers():
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    user = DummyUser([DummyToken("google", expiry)])
    assert compute_token_expiry_for_provider(cast(User, user), "oidc") is None


def test_compute_token_expiry_for_provider_returns_correct_expiry_among_multiple_providers():
    oidc_expiry = datetime.now(timezone.utc) + timedelta(hours=2)
    google_expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
    user = DummyUser([DummyToken("google", google_expiry), DummyToken("oidc", oidc_expiry)])
    result = compute_token_expiry_for_provider(cast(User, user), "oidc")
    assert result == _truncate_to_seconds(oidc_expiry)


def test_compute_token_expiry_for_provider_returns_none_when_token_missing_auth_time_or_expires():
    token = DummyToken.__new__(DummyToken)
    token.provider = "oidc"
    token.extra_data = {}
    user = DummyUser([token])
    assert compute_token_expiry_for_provider(cast(User, user), "oidc") is None


def test_drs_bundle_to_items_flattens_bundle_and_merges_headers(monkeypatch):
    root_uri = "drs://example.org/bundle"
    file_source = _fake_drs_file_source(
        force_http=True,
        http_headers={
            "Authorization": "Bearer from-config",
            "X-Config": "yes",
        },
    )
    upload_config = cast(UploadConfig, SimpleNamespace(file_sources=object()))
    seen_get_drs_object_calls = []

    def mock_get_drs_object(drs_uri, force_http=False, headers=None):
        seen_get_drs_object_calls.append((drs_uri, force_http, headers))
        if drs_uri == root_uri:
            return SimpleNamespace(contents=[ContentsObject(name="child-name.txt", id="child")])
        assert drs_uri == "drs://example.org/child"
        return SimpleNamespace(id="child", name="child-object-name.txt", contents=None)

    monkeypatch.setattr(
        "galaxy.tools.data_fetch_utils.ensure_file_sources",
        lambda file_sources: SimpleNamespace(get_file_source_path=lambda uri: SimpleNamespace(file_source=file_source)),
    )
    monkeypatch.setattr("galaxy.tools.data_fetch_utils.get_drs_object", mock_get_drs_object)

    items = drs_bundle_to_items(
        upload_config,
        {
            "url": root_uri,
            "headers": {
                "Authorization": "Bearer from-target",
            },
        },
    )

    expected_headers = {
        "Authorization": "Bearer from-target",
        "X-Config": "yes",
    }
    assert items == [
        {
            "src": "url",
            "url": "drs://example.org/child",
            "name": "child-name.txt",
            "ext": "auto",
            "headers": expected_headers,
        }
    ]
    assert seen_get_drs_object_calls == [
        (root_uri, True, expected_headers),
        ("drs://example.org/child", True, expected_headers),
    ]


def test_drs_contents_to_items_flattens_nested_bundles_and_prefers_child_drs_uri(monkeypatch):
    seen_get_drs_object_calls = []
    child_uri = "drs://external.example.org/child"
    nested_uri = "drs://example.org/nested"
    headers = {"Authorization": "Bearer token"}

    def mock_get_drs_object(drs_uri, force_http=False, headers=None):
        seen_get_drs_object_calls.append((drs_uri, force_http, headers))
        if drs_uri == child_uri:
            return SimpleNamespace(id="child", name="child-object-name.txt", contents=None)
        if drs_uri == nested_uri:
            return SimpleNamespace(
                id="nested",
                name="nested-object-name",
                contents=[ContentsObject(name="leaf-name.txt", id="leaf")],
            )
        assert drs_uri == "drs://example.org/leaf"
        return SimpleNamespace(id="leaf", name="leaf-object-name.txt", contents=None)

    monkeypatch.setattr("galaxy.tools.data_fetch_utils.get_drs_object", mock_get_drs_object)

    items = _drs_contents_to_items(
        "drs://example.org/root",
        [
            ContentsObject(name="external-name.txt", drs_uri=[child_uri], id="ignored-id"),
            ContentsObject(name="nested-name", id="nested"),
        ],
        force_http=False,
        headers=headers,
    )

    assert items == [
        {
            "src": "url",
            "url": child_uri,
            "name": "external-name.txt",
            "ext": "auto",
            "headers": headers,
        },
        {
            "src": "url",
            "url": "drs://example.org/leaf",
            "name": "leaf-name.txt",
            "ext": "auto",
            "headers": headers,
        },
    ]
    assert seen_get_drs_object_calls == [
        (child_uri, False, headers),
        (nested_uri, False, headers),
        ("drs://example.org/leaf", False, headers),
    ]


def _fake_drs_file_source(force_http=False, http_headers=None):
    return SimpleNamespace(
        plugin_type="drs",
        _get_runtime_context=lambda user_context=None: SimpleNamespace(
            config=SimpleNamespace(force_http=force_http, http_headers=http_headers)
        ),
    )
