from types import SimpleNamespace
from typing import (
    cast,
    TYPE_CHECKING,
)

from galaxy.web.framework.decorators import __extract_payload_from_request
from galaxy.webapps.galaxy.api.tool_shed_repositories import parse_repository_from_payload

if TYPE_CHECKING:
    from galaxy.webapps.base.webapp import GalaxyWebTransaction


def test_form_encoded_numeric_changeset_revision_stays_a_string():
    trans = cast(
        "GalaxyWebTransaction",
        SimpleNamespace(request=SimpleNamespace(headers={"content-type": "application/x-www-form-urlencoded"})),
    )
    payload = __extract_payload_from_request(
        trans,
        lambda: None,
        {
            "tool_shed_url": "http://127.0.0.1:9009",
            "name": "123",
            "owner": "456",
            "changeset_revision": "290925147592",
        },
    )
    assert parse_repository_from_payload(payload) == ("http://127.0.0.1:9009", "123", "456", "290925147592")
