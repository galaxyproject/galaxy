"""Tests for the Galaxy instance file source.

The plugin wraps ``galaxy_fsspec.fs.GalaxyFileSystem`` from the optional ``galaxy-fsspec``
package. These replace that class with an in-memory fake, so the suite runs without the package
and without network access. That works because ``_open_fs`` reads the class off
``required_module``, which is also what the dependency guard checks.
"""

import ipaddress

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

TREE = {
    "": [
        {"name": "histories", "type": "directory", "size": 0},
        {"name": "libraries", "type": "directory", "size": 0},
    ],
    "histories": [{"name": "histories/My History", "type": "directory", "size": 0, "mtime": 1.0}],
    "histories/My History": [{"name": "histories/My History/reads.fastq", "type": "file", "size": 11, "mtime": 2.0}],
    "libraries": [],
}
FILES = {"histories/My History/reads.fastq": b"hello world"}


class FakeRecorder:
    def __init__(self):
        self.init_kwargs: list[dict] = []
        self.closed = 0


def _fake_class(recorder: FakeRecorder):
    class FakeGalaxyFileSystem:
        def __init__(self, **kwargs):
            recorder.init_kwargs.append(dict(kwargs))
            self.dircache = {}

        @staticmethod
        def _key(path):
            return (path or "").strip("/")

        def ls(self, path, detail=True, **kwargs):
            key = self._key(path)
            if key not in TREE:
                raise FileNotFoundError(key)
            entries = TREE[key]
            return entries if detail else [e["name"] for e in entries]

        def walk(self, path, detail=True, **kwargs):
            pending = [self._key(path)]
            while pending:
                key = pending.pop(0)
                entries = TREE.get(key, [])
                dirs = {e["name"]: e for e in entries if e["type"] == "directory"}
                files = {e["name"]: e for e in entries if e["type"] == "file"}
                yield key, dirs, files
                pending.extend(dirs)

        def get_file(self, rpath, lpath, **kwargs):
            with open(lpath, "wb") as handle:
                handle.write(FILES[self._key(rpath)])

        def close(self):
            recorder.closed += 1

    return FakeGalaxyFileSystem


@pytest.fixture
def recorder(monkeypatch) -> FakeRecorder:
    rec = FakeRecorder()
    monkeypatch.setattr(Galaxy2GalaxyFilesSource, "required_module", _fake_class(rec))
    return rec


def _conf(**overrides) -> dict:
    conf = {"type": "galaxy2galaxy", "id": "test1", "base_url": REMOTE, "api_key": API_KEY}
    conf.update(overrides)
    return conf


def _source(conf=None, allowlist=None):
    plugins = FileSourcePluginsConfig(fetch_url_allowlist=allowlist or [])
    sources = configured_file_sources([conf or _conf()], plugins)
    return sources.get_file_source_path("galaxy2galaxy://test1").file_source


def _list(source, path="/", **kwargs):
    kwargs.setdefault("limit", 50)
    kwargs.setdefault("offset", 0)
    return source.list(path, user_context=user_context_fixture(), **kwargs)


def test_plugin_identity(recorder):
    source = _source()
    assert source.plugin_type == "galaxy2galaxy"
    assert source.get_scheme() == "galaxy2galaxy"
    assert source.get_url() == REMOTE
    assert source.writable is False
    assert source.to_dict()["supports"] == {"pagination": True, "search": True, "sorting": False}


def test_the_api_key_is_not_in_the_client_facing_dict(recorder):
    """``to_dict()`` without ``for_serialization`` fills the client's file source list."""
    as_dict = _source().to_dict()
    assert API_KEY not in str(as_dict)


def test_the_api_key_reaches_the_job(recorder):
    """``_serialize_config`` is what a job gets, and it needs both to read anything."""
    serialized = _source().to_dict(for_serialization=True, user_context=user_context_fixture())
    assert serialized["api_key"] == API_KEY
    assert serialized["base_url"] == REMOTE


def test_a_writable_source_is_refused(recorder):
    """The backend raises on every write, so a writable source would fail after being chosen."""
    with pytest.raises(ValueError, match="read-only"):
        _source(_conf(writable=True))


def test_listing_the_root(recorder):
    entries, total = _list(_source())
    assert [entry.name for entry in entries] == ["histories", "libraries"]
    assert total == 2


def test_a_dataset_keeps_its_size_and_date(recorder):
    entries, _ = _list(_source(), "histories/My History")
    assert entries[0].size == 11
    assert entries[0].ctime


def test_realizing_a_dataset(recorder, tmp_path):
    target = tmp_path / "staged"
    _source().realize_to("histories/My History/reads.fastq", str(target), user_context=user_context_fixture())
    assert target.read_bytes() == b"hello world"


def test_writing_is_refused(recorder, tmp_path):
    source_file = tmp_path / "local"
    source_file.write_text("x")
    with pytest.raises(Exception, match="(?i)writ"):
        _source().write_from("histories/My History/x", str(source_file), user_context=user_context_fixture())


def test_a_write_intent_listing_is_refused(recorder):
    """Export pickers ask with this, and a read-only source must not offer itself."""
    with pytest.raises(MessageException, match="read-only"):
        _source().list("/", user_context=user_context_fixture(), opts=FilesSourceOptions(write_intent=True))


def test_a_missing_path_is_a_404(recorder):
    """The shared fsspec layer wraps everything as a generic error, which reads as 400.

    The cause survives on ``__cause__``, so a missing history can still be reported as missing.
    """
    with pytest.raises(ObjectNotFound):
        _list(_source(), "histories/No Such History")


@pytest.mark.parametrize("configured", ["galaxy.example", "ftp://galaxy.example", "https://", ""])
def test_an_address_without_a_protocol_and_host_says_so(recorder, configured):
    """Leaving the protocol off is the obvious thing to do and fails obscurely without this."""
    with pytest.raises(RequestParameterInvalidException, match="protocol and a host"):
        _list(_source(_conf(base_url=configured)))


def test_a_missing_api_key_says_so(recorder):
    """The backend's own error names an environment variable, which is not where this is set."""
    with pytest.raises(AuthenticationRequired, match="API key"):
        _list(_source(_conf(api_key="")))


@pytest.mark.parametrize(
    "configured",
    [
        "http://127.0.0.1:8080",
        "http://169.254.169.254",
        "http://10.0.0.5",
        "HTTP://127.0.0.1",
        "http://[::1]:9200",
    ],
)
def test_an_address_on_this_servers_network_is_refused(recorder, configured):
    """``base_url`` is a user-supplied template variable, so it decides where the key is sent.

    ``validate_non_local`` cannot be handed the raw URL: it tests the scheme with a case-sensitive
    ``startswith``, and it resolves an IPv6 literal with the brackets still on.
    """
    with pytest.raises(ConfigDoesNotAllowException, match="fetch_url_allowlist"):
        _list(_source(_conf(base_url=configured)))


def test_an_allowlisted_private_address_is_allowed(recorder):
    """A Galaxy on a private network is an ordinary thing for an admin to configure."""
    source = _source(
        _conf(base_url="http://127.0.0.1:8080"),
        allowlist=[ipaddress.ip_network("127.0.0.0/8")],
    )
    assert _list(source)[1] == 2


def test_the_filesystem_is_not_shared_between_requests(recorder):
    """fsspec caches one instance per set of arguments for the whole process.

    Without ``skip_instance_cache`` one request's filesystem, and its credentials, would be handed
    to every other request configured the same way.
    """
    _list(_source())
    assert recorder.init_kwargs[0]["skip_instance_cache"] is True
    assert recorder.init_kwargs[0]["url"] == REMOTE
    assert recorder.init_kwargs[0]["api_key"] == API_KEY


def test_the_cache_options_reach_the_filesystem(recorder):
    """Galaxy persists these, so a source must not offer settings that do nothing."""
    _list(_source(_conf(use_listings_cache=False, listings_expiry_time=5, max_paths=7)))
    passed = recorder.init_kwargs[0]
    assert passed["use_listings_cache"] is False
    assert passed["listings_expiry_time"] == 5
    assert passed["max_paths"] == 7
