import json
from types import SimpleNamespace
from typing import (
    cast,
    TYPE_CHECKING,
)

import pytest

from galaxy.web.framework.decorators import __extract_payload_from_request

if TYPE_CHECKING:
    from galaxy.webapps.base.webapp import GalaxyWebTransaction


@pytest.mark.parametrize("content_type", ["application/x-www-form-urlencoded", "multipart/form-data; boundary=test"])
@pytest.mark.parametrize("history_id", ["7456249629763929", "0456249629763929", "40000000000000e5", "e4ca7f1374d5ab51"])
def test_form_history_id_remains_encoded(content_type, history_id):
    trans = cast(
        "GalaxyWebTransaction", SimpleNamespace(request=SimpleNamespace(headers={"content-type": content_type}))
    )
    inputs = {"count": 3, "input1": {"src": "hda", "id": history_id}}
    payload = __extract_payload_from_request(
        trans,
        lambda: None,
        {"history_id": history_id, "inputs": json.dumps(inputs), "count": "3", "ratio": "1.5"},
    )
    assert payload["history_id"] == history_id
    assert payload["inputs"] == inputs
    assert payload["count"] == 3
    assert payload["ratio"] == 1.5
