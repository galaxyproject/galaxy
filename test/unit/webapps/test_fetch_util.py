from unittest.mock import MagicMock

import pytest

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.webapps.galaxy.services._fetch_util import validate_and_normalize_targets


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("unknown://user:secret@example.org/a.bed", "unknown://example.org/a.bed"),
        (
            "unknown://example.org/a?next=ftp://user:secret@inner.example.org/b",
            "unknown://example.org/a?next=ftp://inner.example.org/b",
        ),
        (
            "unknown://example.org/a?next=//user:secret@inner.example.org/b",
            "unknown://example.org/a?next=//inner.example.org/b",
        ),
    ],
)
def test_invalid_url_error_hides_userinfo(url, expected):
    trans = MagicMock()
    trans.app.config.external_chown_script = None
    trans.app.file_sources.looks_like_uri.return_value = False
    payload = {
        "targets": [
            {
                "destination": {"type": "hdas"},
                "elements": [{"src": "url", "url": url}],
            }
        ]
    }

    with pytest.raises(RequestParameterInvalidException) as exc_info:
        validate_and_normalize_targets(trans, payload)

    message = str(exc_info.value)
    assert "secret" not in message
    assert expected in message
