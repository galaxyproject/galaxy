from dataclasses import dataclass

import pytest
from starlette.requests import Request

from galaxy.managers._config_templates import oauth2_redirect_uri
from galaxy.webapps.galaxy.api import GalaxyASGIRequest


@dataclass
class RequestContext:
    request: GalaxyASGIRequest


def request_context(root_path: str) -> RequestContext:
    # Scope as seen by Galaxy's app when mounted at ``galaxy_url_prefix`` (``root_path``).
    scope = {
        "type": "http",
        "scheme": "https",
        "server": ("galaxy.example.org", 443),
        "app_root_path": "",
        "root_path": root_path,
        "path": f"{root_path}/api/file_source_templates/dropbox/0/oauth2",
        "query_string": b"",
        "headers": [],
    }
    return RequestContext(request=GalaxyASGIRequest(Request(scope)))


@pytest.mark.parametrize(
    "galaxy_url_prefix, expected_redirect_uri",
    [
        ("", "https://galaxy.example.org/oauth2_callback"),
        ("/galaxy", "https://galaxy.example.org/galaxy/oauth2_callback"),
    ],
)
def test_oauth2_redirect_uri_points_to_callback_under_url_prefix(galaxy_url_prefix, expected_redirect_uri):
    trans = request_context(galaxy_url_prefix)
    assert oauth2_redirect_uri(trans) == expected_redirect_uri  # type: ignore[arg-type]
