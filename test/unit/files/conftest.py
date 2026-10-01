"""Pytest fixtures for the files unit test suite."""

import time
from collections.abc import Generator

import pytest

from galaxy.util.unittest_utils.test_http_server import test_http_server  # noqa: F401


@pytest.fixture
def non_utc_local_time(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    with monkeypatch.context() as patch:
        patch.setenv("TZ", "Asia/Tokyo")
        time.tzset()
        yield
    time.tzset()
