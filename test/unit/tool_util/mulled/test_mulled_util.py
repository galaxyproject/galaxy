import pytest

from galaxy.tool_util.deps.mulled.util import (
    quay_repository,
    quay_tag_exists,
    QuayApiException,
    version_sorted,
)


class FakeResponse:
    def __init__(self, status_code, payload=None, text="", headers=None, json_error=False):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise ValueError("invalid json")
        return self._payload


class FakeSession:
    def __init__(self, *, get_response=None, head_response=None):
        self.get_response = get_response
        self.head_response = head_response
        self.get_calls = []
        self.head_calls = []

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        return self.get_response

    def head(self, url, **kwargs):
        self.head_calls.append((url, kwargs))
        return self.head_response


@pytest.mark.parametrize(
    "tags,tag",
    [
        (["2.22--he941832_1", "2.22--he860b03_2", "2.22--hdbcaa40_3"], "2.22--hdbcaa40_3"),
        (["1.1.2--py27_0", "1.1.2--py36_0", "1.1.2--py35_0"], "1.1.2--py36_0"),
        (
            ["6725cda82000b8e514baddcbf8c2dce054e3f797-1", "6725cda82000b8e514baddcbf8c2dce054e3f797-0"],
            "6725cda82000b8e514baddcbf8c2dce054e3f797-1",
        ),
        (["python:3.5", "python:3.7", "python:3.7--2"], "python:3.7--2"),
    ],
)
def test_version_sorted(tags, tag):
    assert version_sorted(tags)[0] == tag


def test_quay_tag_exists_uses_registry_head():
    session = FakeSession(head_response=FakeResponse(200))

    assert quay_tag_exists("biocontainers", "samtools", "1.17--0", session=session) is True
    called_url = session.head_calls[0][0]
    assert called_url.startswith("https://quay.io/v2/biocontainers/samtools/manifests/")
    assert called_url.endswith("1.17--0")


def test_quay_tag_exists_returns_false_for_missing_tag():
    session = FakeSession(head_response=FakeResponse(404))

    assert quay_tag_exists("biocontainers", "samtools", "1.17--0", session=session) is False


def test_quay_tag_exists_falls_back_to_repository_metadata(monkeypatch):
    session = FakeSession(head_response=FakeResponse(502, text="", json_error=True))

    monkeypatch.setattr(
        "galaxy.tool_util.deps.mulled.util.quay_repository",
        lambda *args, **kwargs: {"tags": {"1.17--0": {}}},
    )

    assert quay_tag_exists("biocontainers", "samtools", "1.17--0", session=session) is True


def test_quay_tag_exists_does_not_fall_back_for_non_transient_errors(monkeypatch):
    session = FakeSession(head_response=FakeResponse(403, payload={"error_type": "forbidden"}))

    monkeypatch.setattr("galaxy.tool_util.deps.mulled.util.quay_repository", lambda *args, **kwargs: pytest.fail())

    with pytest.raises(QuayApiException):
        quay_tag_exists("biocontainers", "samtools", "1.17--0", session=session)


def test_quay_repository_returns_invalid_token_response_for_401():
    session = FakeSession(get_response=FakeResponse(401, payload={"error_type": "invalid_token"}))

    assert quay_repository("biocontainers", "samtools", session=session) == {"error_type": "invalid_token"}
