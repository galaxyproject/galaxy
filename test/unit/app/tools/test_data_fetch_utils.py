from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import cast

from galaxy.files import (
    ConfiguredFileSources,
    ConfiguredFileSourcesConf,
    DictFileSourcesUserContext,
)
from galaxy.files.models import FileSourcePluginsConfig
from galaxy.model import User
from galaxy.tools.data_fetch_utils import staged_fetch_token_expiration


class DummyToken:
    def __init__(self, expiration_time):
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


def _user_context():
    return DictFileSourcesUserContext(
        username="alice",
        email="alice@example.com",
        preferences={},
        role_names=set(),
        group_names=set(),
        is_admin=False,
        oidc_access_tokens={"oidc": "token"},
    )


def _file_sources():
    return ConfiguredFileSources(
        FileSourcePluginsConfig(),
        ConfiguredFileSourcesConf(
            conf_dict=[
                {
                    "type": "http",
                    "id": "auth_http",
                    "url_regex": r"^https?://auth\.example\.org/",
                    "http_headers": {
                        "Authorization": "Bearer ${user.oidc_access_tokens['oidc']}",
                    },
                },
                {
                    "type": "http",
                    "id": "plain_http",
                    "url_regex": r"^https?://plain\.example\.org/",
                },
            ]
        ),
    )


def test_staged_fetch_token_expiration_returns_none_without_authorization_header():
    user = DummyUser([DummyToken(datetime.now(timezone.utc) + timedelta(hours=1))])
    request = {
        "targets": [
            {
                "destination": {"type": "hdas"},
                "elements": [{"src": "url", "url": "https://plain.example.org/data.txt"}],
            }
        ]
    }
    assert staged_fetch_token_expiration(cast(User, user), request, _file_sources(), _user_context()) is None


def test_staged_fetch_token_expiration_returns_earliest_expiration_for_authorized_sources():
    earliest = datetime.now(timezone.utc) + timedelta(minutes=10)
    later = datetime.now(timezone.utc) + timedelta(hours=2)
    user = DummyUser([DummyToken(later), DummyToken(earliest)])
    request = {
        "targets": [
            {
                "destination": {"type": "hdas"},
                "elements": [{"src": "url", "url": "https://auth.example.org/data.txt"}],
            }
        ]
    }
    assert staged_fetch_token_expiration(
        cast(User, user), request, _file_sources(), _user_context()
    ) == _truncate_to_seconds(earliest)


def test_staged_fetch_token_expiration_ignores_non_authorized_urls_when_authorized_one_exists():
    earliest = datetime.now(timezone.utc) + timedelta(minutes=15)
    user = DummyUser([DummyToken(earliest)])
    request = {
        "targets": [
            {
                "destination": {"type": "hdas"},
                "elements": [
                    {"src": "url", "url": "https://plain.example.org/plain.txt"},
                    {"src": "url", "url": "https://auth.example.org/protected.txt"},
                ],
            }
        ]
    }
    assert staged_fetch_token_expiration(
        cast(User, user), request, _file_sources(), _user_context()
    ) == _truncate_to_seconds(earliest)


def test_staged_fetch_token_expiration_finds_authorized_urls_in_nested_targets():
    earliest = datetime.now(timezone.utc) + timedelta(minutes=20)
    user = DummyUser([DummyToken(earliest)])
    request = {
        "targets": [
            {
                "destination": {"type": "hdca"},
                "collection_type": "list:list",
                "elements": [
                    {
                        "name": "outer",
                        "elements": [{"name": "inner", "src": "url", "url": "https://auth.example.org/nested.txt"}],
                    }
                ],
            }
        ]
    }
    assert staged_fetch_token_expiration(
        cast(User, user), request, _file_sources(), _user_context()
    ) == _truncate_to_seconds(earliest)
