"""Checks the integration test cannot reach: refusals, error translation and what the backend is given.

``required_module`` is swapped for a fake, so these need neither ``galaxy-fsspec`` nor a network.
"""

import pytest

from galaxy.exceptions import (
    AuthenticationRequired,
    ConfigDoesNotAllowException,
    MessageException,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.files.models import FilesSourceOptions
from galaxy.files.plugins import FileSourcePluginsConfig
from galaxy.files.sources.galaxy2galaxy import Galaxy2GalaxyFilesSource
from ._util import (
    configured_file_sources,
    user_context_fixture,
)

REMOTE = "https://galaxy.example"
API_KEY = "test-key"


def _fake(init_kwargs: list, read_error: Exception | None = None):
    class FakeGalaxyFileSystem:
        def __init__(self, **kwargs):
            init_kwargs.append(kwargs)
            self.dircache = {}

        def ls(self, path, detail=True, **kwargs):
            return [{"name": "histories", "type": "directory", "size": 0}]

        def get_file(self, rpath, lpath, **kwargs):
            if read_error:
                raise read_error

    return FakeGalaxyFileSystem


@pytest.fixture
def init_kwargs(monkeypatch) -> list:
    recorded: list = []
    monkeypatch.setattr(Galaxy2GalaxyFilesSource, "required_module", _fake(recorded))
    return recorded


def _source(**overrides):
    conf = {"type": "galaxy2galaxy", "id": "test1", "base_url": REMOTE, "api_key": API_KEY, **overrides}
    sources = configured_file_sources([conf], FileSourcePluginsConfig())
    return sources.get_file_source_path("galaxy2galaxy://test1").file_source


def _list(source):
    return source.list("/", user_context=user_context_fixture(), limit=50, offset=0)


def test_the_api_key_stays_out_of_the_client_list(init_kwargs):
    assert API_KEY not in str(_source().to_dict())


def test_it_is_read_only(init_kwargs):
    with pytest.raises(ValueError, match="read-only"):
        _source(writable=True)
    with pytest.raises(MessageException, match="read-only"):
        _source().list("/", user_context=user_context_fixture(), opts=FilesSourceOptions(write_intent=True))


@pytest.mark.parametrize("configured", ["galaxy.example", "https://"])
def test_an_address_without_a_protocol_and_host_says_so(init_kwargs, configured):
    with pytest.raises(RequestParameterInvalidException, match="protocol and a host"):
        _list(_source(base_url=configured))


def test_a_missing_api_key_says_so(init_kwargs):
    with pytest.raises(AuthenticationRequired, match="API key"):
        _list(_source(api_key=""))


@pytest.mark.parametrize(
    "configured",
    ["http://127.0.0.1:8080", "http://169.254.169.254", "http://10.0.0.5", "HTTP://127.0.0.1", "http://[::1]:9200"],
)
def test_an_address_on_this_servers_network_is_refused(init_kwargs, configured):
    """base_url is user supplied, so it decides where the key goes. The odd spellings get past
    validate_non_local when it is handed the raw URL."""
    with pytest.raises(ConfigDoesNotAllowException, match="fetch_url_allowlist"):
        _list(_source(base_url=configured))


def test_each_request_gets_its_own_filesystem_with_the_cache_options(init_kwargs):
    _list(_source(use_listings_cache=False, listings_expiry_time=5, max_paths=7))
    passed = init_kwargs[0]
    assert passed["skip_instance_cache"] is True
    assert (passed["url"], passed["api_key"]) == (REMOTE, API_KEY)
    assert (passed["use_listings_cache"], passed["listings_expiry_time"], passed["max_paths"]) == (False, 5, 7)


class FakeBioblendConnectionError(Exception):
    """Like bioblend.ConnectionError: named after the builtin, but not an OSError."""


@pytest.mark.parametrize(
    "raised,expected",
    [
        (FileNotFoundError("gone"), ObjectNotFound),
        (PermissionError("refused"), AuthenticationRequired),
        (OSError("has no data to read yet (state 'running')"), MessageException),
        (FakeBioblendConnectionError("GET: error 401: Provided API key is not valid."), MessageException),
    ],
)
def test_a_failed_read_is_explained_rather_than_a_server_error(monkeypatch, tmp_path, raised, expected):
    monkeypatch.setattr(Galaxy2GalaxyFilesSource, "required_module", _fake([], read_error=raised))
    with pytest.raises(expected) as caught:
        _source().realize_to("histories/h/reads.fastq", str(tmp_path / "staged"), user_context=user_context_fixture())
    assert caught.value.__cause__ is raised
    if expected is MessageException:
        assert str(raised) in str(caught.value)
