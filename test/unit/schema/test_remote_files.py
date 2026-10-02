from datetime import (
    datetime,
    timezone,
)

import pytest
from pydantic import ValidationError

from galaxy.schema.remote_files import ListUriResponse

REMOTE_FILE = {"class": "File", "name": "a", "uri": "gxfiles://test1/a", "path": "/a", "size": 1}


def test_list_uri_response_serializes_ctime_as_utc():
    response = ListUriResponse.model_validate(
        [{**REMOTE_FILE, "ctime": datetime(2024, 1, 15, 10, 20, 30, tzinfo=timezone.utc)}]
    )
    assert '"ctime":"2024-01-15T10:20:30Z"' in response.model_dump_json()


def test_list_uri_response_accepts_null_ctime():
    response = ListUriResponse.model_validate([{**REMOTE_FILE, "ctime": None}])
    assert '"ctime":null' in response.model_dump_json()


def test_list_uri_response_requires_ctime():
    with pytest.raises(ValidationError):
        ListUriResponse.model_validate([REMOTE_FILE])
