from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import cast

from galaxy.model import User
from galaxy.tools.data_fetch_utils import compute_token_expiry_for_provider


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
