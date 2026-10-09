"""Refusals the integration test cannot reach, since it points the source at this Galaxy on loopback.

``required_module`` is swapped for a placeholder, so these need neither ``galaxy-fsspec`` nor a network.
"""

import pytest

from galaxy.exceptions import MessageException
from galaxy.files.plugins import FileSourcePluginsConfig
from galaxy.files.sources.galaxy2galaxy import Galaxy2GalaxyFilesSource
from ._util import (
    configured_file_sources,
    user_context_fixture,
)

# An address rather than a name, so the private-address check does no DNS lookup.
REMOTE = "https://1.2.3.4"


@pytest.fixture(autouse=True)
def backend(monkeypatch):
    # Each check refuses before the backend is built, but the source does not load without one.
    monkeypatch.setattr(Galaxy2GalaxyFilesSource, "required_module", object)


def _list(**overrides):
    conf = {"type": "galaxy2galaxy", "id": "test1", "base_url": REMOTE, "api_key": "test-key", **overrides}
    sources = configured_file_sources([conf], FileSourcePluginsConfig())
    return sources.get_file_source_path("galaxy2galaxy://test1").file_source.list(
        "/", user_context=user_context_fixture()
    )


@pytest.mark.parametrize("configured", ["galaxy.example", "https://"])
def test_an_address_without_a_protocol_and_host_says_so(configured):
    with pytest.raises(MessageException, match="protocol and a host"):
        _list(base_url=configured)


def test_a_missing_api_key_says_so():
    with pytest.raises(MessageException, match="no API key"):
        _list(api_key="")


@pytest.mark.parametrize(
    "configured",
    ["http://127.0.0.1:8080", "http://169.254.169.254", "http://10.0.0.5", "HTTP://127.0.0.1", "http://[::1]:9200"],
)
def test_an_address_on_this_servers_network_is_refused(configured):
    """base_url is user supplied, so it decides where the key goes. The odd spellings get past
    validate_non_local when it is handed the raw URL."""
    with pytest.raises(MessageException, match="fetch_url_allowlist"):
        _list(base_url=configured)
